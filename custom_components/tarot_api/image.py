"""Tarot card face as a Home Assistant `image` entity for Picture cards."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TarotHub
from .const import DOMAIN, PLACEHOLDER_CARD_IMAGE, PROVIDER_KRATES, SIGNAL_CARD_UPDATED

_CACHED_PROP_KEYS = frozenset({"image_url", "image_last_updated", "content_type"})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up image platform."""
    hub: TarotHub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TarotCardImage(hass, entry, hub)], True)


class TarotCardImage(ImageEntity):
    """Serves the current card art via HA's image proxy (Picture entity cards accept this)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, hub: TarotHub) -> None:
        super().__init__(hass)
        self._entry = entry
        self._hub = hub
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_face"
        self._attr_name = "Tarot card face"
        self._apply_image()

    def _invalidate_image_cache_props(self) -> None:
        """ImageEntity uses cached_property; refresh after URL/time changes."""
        for key in _CACHED_PROP_KEYS:
            self.__dict__.pop(key, None)

    def _apply_image(self) -> None:
        card = self._hub.last_card
        if card and card.get("image_url"):
            self._attr_image_url = str(card["image_url"])
        else:
            self._attr_image_url = PLACEHOLDER_CARD_IMAGE
        self._cached_image = None
        self._invalidate_image_cache_props()
        self._attr_image_last_updated = datetime.now(timezone.utc)

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

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _on_update(_data: dict) -> None:
            if _data.get("entry_id") == self._entry.entry_id:
                self._apply_image()
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_CARD_UPDATED, _on_update)
        )
