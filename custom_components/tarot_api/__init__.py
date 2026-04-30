"""Home Assistant integration for Tarot APIs with optional card images."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_BASE_URL,
    CONF_PROVIDER,
    DEFAULT_BASE_URL,
    DOMAIN,
    EKELEN_RANDOM_PATH,
    KRATES_RANDOM_PATH,
    PROVIDER_EKELEN,
    PROVIDER_KRATES,
    SIGNAL_CARD_UPDATED,
)
from .image_util import image_url_for_ekelen_card

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.SENSOR,
]


@dataclass
class TarotHub:
    """Holds API client state and last draw."""

    hass: HomeAssistant
    entry_id: str
    base_url: str
    provider: str
    last_card: dict[str, Any] | None = None
    orientation: str | None = None  # "upright" | "reversed"

    async def async_draw_one(self) -> None:
        """Fetch one random card and store it with a random orientation."""
        if self.provider == PROVIDER_KRATES:
            await self._async_draw_krates()
        else:
            await self._async_draw_ekelen()

    async def _async_draw_ekelen(self) -> None:
        session = async_get_clientsession(self.hass)
        url = f"{self.base_url.rstrip('/')}{EKELEN_RANDOM_PATH}?n=1"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Tarot API request failed: %s", err)
            raise HomeAssistantError(f"Tarot API request failed: {err}") from err

        cards = data.get("cards") or []
        if not cards:
            raise HomeAssistantError("Tarot API returned no cards")

        raw = dict(cards[0])
        raw["image_url"] = image_url_for_ekelen_card(raw)
        raw["_provider"] = PROVIDER_EKELEN
        self.last_card = raw
        self.orientation = random.choice(["upright", "reversed"])
        async_dispatcher_send(
            self.hass, SIGNAL_CARD_UPDATED, {"entry_id": self.entry_id}
        )

    async def _async_draw_krates(self) -> None:
        """Random card from krates98/tarotcardapi-style server (GET /cards/onecard)."""
        session = async_get_clientsession(self.hass)
        url = f"{self.base_url.rstrip('/')}{KRATES_RANDOM_PATH}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Tarot Card API request failed: %s", err)
            raise HomeAssistantError(f"Tarot Card API request failed: {err}") from err

        name = str(data.get("name") or "")
        description = str(data.get("description") or "")
        rel_image = str(data.get("image") or "").strip()
        if not name:
            raise HomeAssistantError("Tarot Card API returned no card name")

        if rel_image.startswith("http"):
            image_url = rel_image
        elif rel_image:
            image_url = urljoin(self.base_url.rstrip("/") + "/", rel_image.lstrip("/"))
        else:
            image_url = None

        self.last_card = {
            "_provider": PROVIDER_KRATES,
            "name": name,
            "desc": description,
            "meaning_up": description,
            "meaning_rev": "",
            "image_url": image_url,
        }
        self.orientation = random.choice(["upright", "reversed"])
        async_dispatcher_send(
            self.hass, SIGNAL_CARD_UPDATED, {"entry_id": self.entry_id}
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tarot API from a config entry."""
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    provider = entry.data.get(CONF_PROVIDER, PROVIDER_EKELEN)
    hub = TarotHub(
        hass=hass,
        entry_id=entry.entry_id,
        base_url=base_url,
        provider=provider,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Add provider key for entries created before multi-provider support."""
    if config_entry.version > 1:
        return True

    data = dict(config_entry.data)
    if CONF_PROVIDER not in data:
        data[CONF_PROVIDER] = PROVIDER_EKELEN
    base = data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    new_unique_id = f"{data[CONF_PROVIDER]}_{base}"
    hass.config_entries.async_update_entry(
        config_entry,
        data=data,
        version=2,
        unique_id=new_unique_id,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
