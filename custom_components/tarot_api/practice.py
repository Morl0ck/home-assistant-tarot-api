"""Local daily practices, with entry-scoped persistent redraws."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import logging
from pathlib import Path
import random
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SIGNAL_PRACTICE_UPDATED = f"{DOMAIN}_practice_updated"
PRACTICES = {
    "affirmation": ("Daily affirmation", "mdi:heart-outline", "New affirmation"),
    "oracle": ("Oracle card", "mdi:star-four-points-outline", "Draw oracle card"),
    "deity": ("Deity card", "mdi:moon-waning-crescent", "Draw deity card"),
    "rune": ("Rune", "mdi:alphabet-runic", "Draw rune"),
}
_CACHE_KEY = f"{DOMAIN}_practice_load"


def load_practices() -> dict[str, list[dict[str, Any]]]:
    """Validate bundled original content in an executor."""
    try:
        data = json.loads(Path(__file__).with_name("practices.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            raise ValueError("Unsupported practice catalog")
        result = {}
        for kind in PRACTICES:
            records = data.get(kind)
            if not isinstance(records, list) or len(records) < 2:
                raise ValueError(f"Missing practice collection: {kind}")
            ids = set()
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError(f"Invalid {kind} record")
                for key in ("id", "name", "interpretation", "reflection", "practice", "symbol"):
                    if not isinstance(record.get(key), str) or not record[key].strip():
                        raise ValueError(f"Missing {kind}/{key}")
                if len(record["name"]) > 255 or record["id"] in ids:
                    raise ValueError(f"Invalid or duplicate {kind} identity")
                keywords = record.get("keywords")
                if not isinstance(keywords, list) or not keywords or not all(isinstance(k, str) and k.strip() for k in keywords):
                    raise ValueError(f"Invalid {kind} keywords")
                ids.add(record["id"])
            result[kind] = records
        return result
    except (OSError, UnicodeError, ValueError) as err:
        _LOGGER.warning("Bundled practices unavailable: %s", err)
        return {}


async def async_get_practices(hass: HomeAssistant) -> dict[str, list[dict[str, Any]]]:
    """Share the executor load across all entries and reloads."""
    load = hass.data.get(_CACHE_KEY)
    if load is None:
        load = hass.async_add_executor_job(load_practices)
        hass.data[_CACHE_KEY] = load
    return await asyncio.shield(load)


class PracticeHub:
    """One shared daily selection per category and Home Assistant entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str, catalog: dict) -> None:
        self.hass = hass
        self.entry_id = entry_id
        # An entry-specific permutation cycles through every item before repeating.
        self.catalog = {
            kind: sorted(records, key=lambda r: hashlib.sha256(f"{entry_id}:{kind}:{r['id']}".encode()).digest())
            for kind, records in catalog.items()
        }
        self.date = dt_util.now().date()
        self.selections: dict[str, str] = {}
        self._store = Store(hass, 1, f"{DOMAIN}_practice_{entry_id}")
        self._lock = asyncio.Lock()
        self._unsubscribe = None

    async def async_start(self) -> None:
        saved = await self._store.async_load()
        if isinstance(saved, dict) and saved.get("date") == self.date.isoformat():
            selections = saved.get("selections")
            if isinstance(selections, dict):
                for kind, record_id in selections.items():
                    if any(r["id"] == record_id for r in self.catalog.get(kind, [])):
                        self.selections[kind] = record_id
        self._unsubscribe = async_track_time_interval(self.hass, self._tick, timedelta(minutes=1))

    def stop(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    @callback
    def _tick(self, _now: Any) -> None:
        """Use the configured HA timezone; also handle clock/timezone changes."""
        if self._refresh_date():
            self._notify()

    def _refresh_date(self) -> bool:
        today = dt_util.now().date()
        if today == self.date:
            return False
        self.date = today
        self.selections = {}
        return True

    def _notify(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_PRACTICE_UPDATED, {"entry_id": self.entry_id})

    def current(self, kind: str) -> dict[str, Any] | None:
        records = self.catalog.get(kind, [])
        if not records:
            return None
        selected_id = self.selections.get(kind)
        record = next((r for r in records if r["id"] == selected_id), records[self.date.toordinal() % len(records)])
        return {**deepcopy(record), "date": self.date.isoformat(), "category": kind}

    async def async_draw(self, kind: str) -> None:
        """Persist before publishing so redraws survive restart and errors."""
        async with self._lock:
            if self._refresh_date():
                self._notify()
            records = self.catalog.get(kind, [])
            current = self.current(kind)
            if current is None:
                return
            chosen = random.choice([r for r in records if r["id"] != current["id"]])
            selections = {**self.selections, kind: chosen["id"]}
            await self._store.async_save({"date": self.date.isoformat(), "selections": selections})
            # A slow disk write may have crossed local midnight.
            if not self._refresh_date():
                self.selections = selections
            self._notify()
