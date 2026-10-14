"""Sensor for the last drawn tarot card."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TarotHub
from .const import DOMAIN, PLACEHOLDER_CARD_IMAGE, PROVIDER_KRATES, SIGNAL_CARD_UPDATED
from .practice import PRACTICES, SIGNAL_PRACTICE_UPDATED
from .horoscope import SIGNAL_HOROSCOPE_UPDATED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tarot sensor from a config entry."""
    hub: TarotHub = hass.data[DOMAIN][entry.entry_id]
    entities = [TarotCardSensor(entry, hub)]
    if hub.horoscope is not None:
        entities.append(HoroscopeSensor(entry, hub))
    if hub.practice is not None:
        entities.extend(PracticeSensor(entry, hub, kind) for kind in PRACTICES)
    async_add_entities(entities, True)


class HoroscopeSensor(SensorEntity):
    """All twelve readings in one small, entry-scoped cache entity."""

    _attr_should_poll = False
    _attr_name = "Daily horoscope"
    _attr_icon = "mdi:zodiac-aquarius"

    def __init__(self, entry: ConfigEntry, hub: TarotHub) -> None:
        self._entry, self._hub = entry, hub
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_horoscope"

    @property
    def native_value(self) -> str | None:
        return max((r["date"] for r in self._hub.horoscope.readings.values()), default=None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._hub.horoscope.attributes

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)}, name="Tarot draw")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def updated(data: dict) -> None:
            if data.get("entry_id") == self._entry.entry_id:
                self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_HOROSCOPE_UPDATED, updated))


class PracticeSensor(SensorEntity):
    """Expose complete local readings for dashboards and automations."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, hub: TarotHub, kind: str) -> None:
        self._entry, self._hub, self._kind = entry, hub, kind
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_practice_{kind}"
        self._attr_name, self._attr_icon, _ = PRACTICES[kind]

    @property
    def available(self) -> bool:
        return self._hub.practice.current(self._kind) is not None

    @property
    def native_value(self) -> str | None:
        record = self._hub.practice.current(self._kind)
        return record["name"] if record else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._hub.practice.current(self._kind) or {}

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)}, name="Tarot draw")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _on_update(data: dict) -> None:
            if data.get("entry_id") == self._entry.entry_id:
                self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_PRACTICE_UPDATED, _on_update))


class TarotCardSensor(SensorEntity):
    """Shows the current / last drawn card."""

    _attr_icon = "mdi:cards-playing-outline"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, hub: TarotHub) -> None:
        self._entry = entry
        self._hub = hub
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_card"
        self._attr_name = "Tarot card"
        self._apply_entity_picture()

    def _apply_entity_picture(self) -> None:
        """Picture-entity / frontend read _attr_entity_picture; keep it in sync with the hub."""
        card = self._hub.last_card
        if card and card.get("image_url"):
            self._attr_entity_picture = str(card["image_url"])
        else:
            self._attr_entity_picture = PLACEHOLDER_CARD_IMAGE

    @property
    def entity_picture(self) -> str | None:
        """Mirror the image entity's authenticated proxy, including solar changes."""
        face = self._hub.face_image
        if face is not None and face.entity_id:
            return face.entity_picture
        return self._attr_entity_picture

    @property
    def native_value(self) -> str | None:
        """Card title, or None if not drawn yet."""
        card = self._hub.last_card
        if not card:
            return None
        name = card.get("name")
        if self._hub.orientation == "reversed" and name:
            return f"{name} (reversed)"
        return name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Existing provider attributes plus the active bundled reading."""
        card = self._hub.last_card
        if not card:
            return {}
        orientation = self._hub.orientation or "upright"
        meaning_up = card.get("meaning_up", "")
        meaning_rev = card.get("meaning_rev", "")
        active_meaning = meaning_rev if orientation == "reversed" else meaning_up
        attrs: dict[str, Any] = {
            "orientation": orientation,
            "meaning": active_meaning,
            "meaning_up": meaning_up,
            "meaning_rev": meaning_rev,
            "description": card.get("desc"),
            "image_url": card.get("image_url"),
        }
        if card.get("_provider") != PROVIDER_KRATES:
            attrs["type"] = card.get("type")
            attrs["name_short"] = card.get("name_short")
            attrs["value"] = card.get("value")
        attrs.update(
            self._hub.readings.attributes_for(card, self._hub.provider, orientation)
        )
        if self._hub.face_image is not None:
            attrs["artwork_theme"] = self._hub.face_image.artwork_theme
            attrs["artwork_url"] = self.entity_picture
        return attrs

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
                self._apply_entity_picture()
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_CARD_UPDATED, _on_update)
        )
