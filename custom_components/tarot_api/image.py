"""Tarot card face as a Home Assistant `image` entity for Picture cards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from uuid import uuid4

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TarotHub
from .artwork import ARTWORK_ROOT, CARD_IDS, card_id_for, current_theme
from .const import DOMAIN, PLACEHOLDER_CARD_IMAGE, PROVIDER_KRATES, SIGNAL_CARD_UPDATED

_CACHED_PROP_KEYS = frozenset({"image_url", "image_last_updated", "content_type"})
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up image platform."""
    hub: TarotHub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TarotCardImage(hass, entry, hub), *(TarotCardImage(hass, entry, hub, index) for index in range(3))], True)


class TarotCardImage(ImageEntity):
    """Serves the current card art via HA's image proxy (Picture entity cards accept this)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, hub: TarotHub, spread_index: int | None = None) -> None:
        super().__init__(hass)
        self._entry = entry
        self._hub = hub
        self._spread_index = spread_index
        if spread_index is None:
            hub.face_image = self
        else:
            hub.spread_images[spread_index] = self
        self._source_key = None
        self._local_bytes = None
        self._failed_paths = set()
        self._last_proxy_url = None
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_face" if spread_index is None else f"{uid}_spread_face_{spread_index + 1}"
        self._attr_name = "Tarot card face" if spread_index is None else f"Tarot spread card {spread_index + 1}"
        self._apply_image()

    @property
    def _card(self) -> dict | None:
        if self._spread_index is None:
            return self._hub.last_card
        cards = self._hub.spread_cards
        return cards[self._spread_index] if self._spread_index < len(cards) else None

    def _invalidate_image_cache_props(self) -> None:
        """ImageEntity uses cached_property; refresh after URL/time changes."""
        for key in _CACHED_PROP_KEYS:
            self.__dict__.pop(key, None)

    def _apply_image(self) -> bool:
        card = self._card
        theme = current_theme(self._hub.hass)
        card_id = card_id_for(self._hub) if self._spread_index is None else (card or {}).get("name_short")
        if card_id not in CARD_IDS:
            card_id = None
        source_key = (theme, card_id, (card or {}).get("image_url"))
        if source_key == self._source_key:
            return False
        self._source_key = source_key
        self._image_revision = uuid4().hex
        self._local_path = ARTWORK_ROOT / theme / f"{card_id}.png" if card_id else None
        self._local_bytes = None
        self._attr_content_type = "image/png" if card_id else "image/jpeg"
        if card and card.get("image_url"):
            self._attr_image_url = str(card["image_url"])
        else:
            self._attr_image_url = PLACEHOLDER_CARD_IMAGE
        self._cached_image = None
        self._invalidate_image_cache_props()
        self._attr_image_last_updated = datetime.now(timezone.utc)
        return True

    @property
    def entity_picture(self) -> str | None:
        """Give each artwork change its own URL while retaining HA authentication."""
        self._apply_image()
        url = super().entity_picture
        if not url:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}v={self._image_revision}"

    @property
    def artwork_theme(self) -> str | None:
        """The selected custom deck, or None for an unrecognized card."""
        self._apply_image()
        return self._source_key[0] if self._local_path else None

    async def async_image(self) -> bytes | None:
        """Serve original PNG bytes through HA's image proxy, outside the event loop."""
        self._apply_image()
        path = self._local_path
        if path is not None and path not in self._failed_paths:
            if self._local_bytes is not None:
                return self._local_bytes
            try:
                content = await self.hass.async_add_executor_job(path.read_bytes)
                if not content.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("Invalid bundled PNG")
            except (OSError, ValueError) as err:
                self._failed_paths.add(path)
                _LOGGER.warning("Bundled tarot artwork unavailable: %s: %s", path, err)
            else:
                if path == self._local_path:
                    self._local_bytes = content
                return content
        # Unknown cards or incomplete manual installations keep provider artwork.
        self._attr_content_type = "image/jpeg"
        self._invalidate_image_cache_props()
        return await super().async_image()

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
                self._last_proxy_url = self.entity_picture
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_CARD_UPDATED, _on_update)
        )

        @callback
        def _on_solar_update(_event) -> None:
            changed = self._apply_image()
            # Keep the sensor's proxy URL current when HA rotates image tokens.
            url = self.entity_picture
            if changed or url != self._last_proxy_url:
                self._last_proxy_url = url
                async_dispatcher_send(
                    self.hass, SIGNAL_CARD_UPDATED, {"entry_id": self._entry.entry_id}
                )

        self._last_proxy_url = self.entity_picture

        self.async_on_remove(
            async_track_state_change_event(self.hass, ["sun.sun"], _on_solar_update)
        )
        # Also handle an absent/unavailable Sun entity and location changes.
        self.async_on_remove(
            async_track_time_interval(self.hass, _on_solar_update, timedelta(minutes=1))
        )
