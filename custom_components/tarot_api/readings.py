"""Load and resolve the bundled Rider–Waite–Smith readings."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import re
from typing import Any
import unicodedata

from homeassistant.core import HomeAssistant

from .const import DOMAIN, PROVIDER_KRATES

_LOGGER = logging.getLogger(__name__)
_CACHE_KEY = f"{DOMAIN}_readings_load"
_RANKS = ("ac", *(f"{rank:02d}" for rank in range(2, 11)), "pa", "kn", "qu", "ki")
_EXPECTED_IDS = frozenset(
    [f"ar{number:02d}" for number in range(22)]
    + [f"{suit}{rank}" for suit in ("wa", "cu", "pe", "sw") for rank in _RANKS]
)
_NAME_ALIASES = {
    "fortitude": "ar08",
    "judgment": "ar20",
    "last judgment": "ar20",
    "last judgement": "ar20",
}


def normalize_card_name(name: str) -> str:
    """Normalize raw provider names while retaining exact identity matching."""
    normalized = unicodedata.normalize("NFKC", name).casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return " ".join(normalized.split()).removeprefix("the ")


@dataclass(frozen=True)
class ReadingCatalog:
    """Shared catalog; callers receive a fresh copy of active attributes."""

    cards: dict[str, dict[str, Any]] = field(default_factory=dict)
    name_index: dict[str, str] = field(default_factory=dict)

    def attributes_for(
        self, card: dict[str, Any], provider: str, orientation: str
    ) -> dict[str, Any]:
        """Return local text or an explicit unavailable reading for this card."""
        if provider == PROVIDER_KRATES:
            name = card.get("name")
            card_id = (
                self.name_index.get(normalize_card_name(name))
                if isinstance(name, str)
                else None
            )
        else:
            raw_id = card.get("name_short")
            card_id = raw_id if isinstance(raw_id, str) else None

        record = self.cards.get(card_id) if card_id is not None else None
        if not isinstance(record, dict):
            record = {}
        raw_name = card.get("name")
        fallback_name = raw_name.strip() if isinstance(raw_name, str) else ""
        attrs: dict[str, Any] = {
            "card_name": record.get("name") or fallback_name or "Unknown card",
            "keywords": [],
            "interpretation": None,
            "reflection": None,
            "reading_available": False,
        }
        active = record.get(orientation)
        if isinstance(active, dict) and _valid_reading(active):
            attrs.update(
                keywords=list(active["keywords"]),
                interpretation=active["interpretation"],
                reflection=active["reflection"],
                reading_available=True,
            )
        return attrs


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_reading(reading: dict[str, Any]) -> bool:
    """Check the fields needed for a complete display."""
    keywords = reading.get("keywords")
    return (
        isinstance(keywords, list)
        and len(keywords) == 3
        and all(_nonempty_text(keyword) for keyword in keywords)
        and len({keyword.casefold() for keyword in keywords}) == 3
        and _nonempty_text(reading.get("interpretation"))
        and _nonempty_text(reading.get("reflection"))
    )


def _unique_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate reading field: {key}")
        result[key] = value
    return result


def _parse_catalog(data: Any) -> ReadingCatalog:
    """Validate the schema and build the provider name index once."""
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or data.get("deck") != "rider-waite-smith"
        or data.get("voice") != "traditional-warm-reflective"
    ):
        raise ValueError("Unsupported tarot readings metadata")

    cards = data.get("cards")
    if not isinstance(cards, dict) or set(cards) != _EXPECTED_IDS:
        raise ValueError("Tarot readings must contain the exact 78 canonical IDs")

    names = {}
    for card_id, card in cards.items():
        if not isinstance(card, dict) or not _nonempty_text(card.get("name")):
            raise ValueError(f"Invalid card name for {card_id}")
        for orientation in ("upright", "reversed"):
            reading = card.get(orientation)
            if not isinstance(reading, dict) or not _valid_reading(reading):
                raise ValueError(f"Incomplete reading for {card_id}/{orientation}")
        name = normalize_card_name(card["name"])
        if not name or name in names:
            raise ValueError(f"Ambiguous card name for {card_id}")
        names[name] = card_id
    for alias, card_id in _NAME_ALIASES.items():
        if alias in names and names[alias] != card_id:
            raise ValueError(f"Ambiguous card alias: {alias}")
        names[alias] = card_id
    return ReadingCatalog(cards, names)


def load_readings() -> ReadingCatalog:
    """Read, parse, validate and index locally; run only in an executor."""
    try:
        with Path(__file__).with_name("readings.json").open(encoding="utf-8") as handle:
            data = json.load(handle, object_pairs_hook=_unique_json_keys)
        return _parse_catalog(data)
    except (OSError, UnicodeError, ValueError) as err:
        _LOGGER.warning("Bundled tarot readings unavailable: %s", err)
        return ReadingCatalog()


async def async_get_readings(hass: HomeAssistant) -> ReadingCatalog:
    """Share one executor load across setups, reloads and concurrent entries."""
    load = hass.data.get(_CACHE_KEY)
    if load is None:
        load = hass.async_add_executor_job(load_readings)
        hass.data[_CACHE_KEY] = load
    # Cancelling an individual setup must not cancel the shared catalog load.
    return await asyncio.shield(load)
