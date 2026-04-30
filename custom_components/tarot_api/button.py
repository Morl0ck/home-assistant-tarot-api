"""Button to draw one tarot card."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TarotHub
from .const import DOMAIN, PROVIDER_KRATES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tarot button from a config entry."""
    hub: TarotHub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TarotDrawButton(entry, hub)], True)


class TarotDrawButton(ButtonEntity):
    """Draws one random card from the API."""

    _attr_icon = "mdi:cards-playing"
    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, hub: TarotHub) -> None:
        self._entry = entry
        self._hub = hub
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_draw"
        self._attr_name = "Draw tarot card"

    async def async_press(self) -> None:
        """Fetch a new random card."""
        await self._hub.async_draw_one()

    @property
    def device_info(self) -> DeviceInfo:
        manuf = (
            "github.com/krates98/tarotcardapi"
            if self._hub.provider == PROVIDER_KRATES
            else "tarotapi.dev"
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Tarot draw",
            manufacturer=manuf,
            model="RWS deck",
        )
