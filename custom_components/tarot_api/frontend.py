"""Serve cards and a first-open installer for native, user-owned dashboards."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .practice import PRACTICES

FRONTEND_VERSION = "1.5.0"
STATIC_URL = "/tarot_api_static"
FRONTEND_ROOT = Path(__file__).parent / "frontend"
_STATIC_KEY = f"{DOMAIN}_frontend_static"


async def _async_register_static(hass: HomeAssistant) -> None:
    """Use async HTTP registration on modern HA; retain pre-2024.7 support."""
    if hasattr(hass.http, "async_register_static_paths"):
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths([
            StaticPathConfig(STATIC_URL, str(FRONTEND_ROOT), False)
        ])
    else:
        # This API only exists on older HA releases. Modern HA never uses it.
        hass.http.register_static_path(STATIC_URL, str(FRONTEND_ROOT), False)
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/moon-practice-card.js?v={FRONTEND_VERSION}")


async def async_register_assets(hass: HomeAssistant) -> None:
    """One route per HA process, including concurrent entries and reloads."""
    task = hass.data.get(_STATIC_KEY)
    if task is None:
        task = asyncio.create_task(_async_register_static(hass))
        hass.data[_STATIC_KEY] = task
    try:
        await asyncio.shield(task)
    except Exception:
        if hass.data.get(_STATIC_KEY) is task:
            hass.data.pop(_STATIC_KEY)
        raise


class PracticeFrontend:
    """A generated panel that follows registry names and cleans up on unload."""

    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        self.hass, self.entry = hass, entry
        self.path = f"tarot-practice-{entry.entry_id}"
        self.dashboard_path = f"daily-practice-{entry.entry_id}"
        self._registry = er.async_get(hass)
        self._unsubscribe = None
        self._unsubscribe_dashboard = None
        self._entity_ids: set[str] = set()

    async def async_start(self) -> None:
        await async_register_assets(self.hass)
        self._refresh_panel()
        self._unsubscribe = self.hass.bus.async_listen(
            "entity_registry_updated", self._on_registry_update
        )
        self._unsubscribe_dashboard = self.hass.bus.async_listen("lovelace_updated", self._on_dashboard_update)

    @callback
    def _on_dashboard_update(self, event: Any) -> None:
        if event.data.get("url_path") == self.dashboard_path:
            self._refresh_panel()

    @callback
    def _on_registry_update(self, event: Any) -> None:
        entity_id = event.data.get("entity_id")
        record = self._registry.async_get(entity_id) if entity_id else None
        if entity_id in self._entity_ids or (record is not None and record.config_entry_id == self.entry.entry_id):
            self._refresh_panel()

    @callback
    def _refresh_panel(self) -> None:
        uid = self.entry.unique_id or self.entry.entry_id
        card = {}
        for kind in ("tarot", *PRACTICES):
            sensor_uid = f"{uid}_card" if kind == "tarot" else f"{uid}_practice_{kind}"
            button_uid = f"{uid}_draw" if kind == "tarot" else f"{uid}_practice_draw_{kind}"
            card[kind] = {
                "entity": self._registry.async_get_entity_id("sensor", DOMAIN, sensor_uid)
                or f"sensor.tarot_api_missing_{kind}",
                "button": self._registry.async_get_entity_id("button", DOMAIN, button_uid)
                or f"button.tarot_api_missing_{kind}",
            }
        card["horoscope"] = {
            "entity": self._registry.async_get_entity_id("sensor", DOMAIN, f"{uid}_horoscope") or "sensor.tarot_api_missing_horoscope",
            "button": self._registry.async_get_entity_id("button", DOMAIN, f"{uid}_horoscope_refresh") or "button.tarot_api_missing_horoscope",
        }
        self._entity_ids = {entity_id for mapping in card.values() for entity_id in mapping.values()}
        existing = self.hass.data.get(frontend.DATA_PANELS, {}).get(self.path)
        if existing is not None and (existing.config or {}).get("tarot_api_entry_id") != self.entry.entry_id:
            raise ValueError(f"Sidebar path {self.path} is already owned by another panel")
        dashboard = self.hass.data.get(frontend.DATA_PANELS, {}).get(self.dashboard_path)
        if dashboard is not None and dashboard.component_name == "lovelace":
            # Native dashboards persist independently. Never rewrite their config.
            if existing is not None:
                frontend.async_remove_panel(self.hass, self.path)
            return
        frontend.async_register_built_in_panel(
            self.hass,
            component_name="custom",
            sidebar_title="Daily Practice",
            sidebar_icon="mdi:moon-waning-crescent",
            frontend_url_path=self.path,
            require_admin=False,
            update=existing is not None,
            config={
                "tarot_api_entry_id": self.entry.entry_id,
                "card": card,
                "dashboard_path": self.dashboard_path,
                "unique_prefix": uid,
                "_panel_custom": {
                    "name": "tarot-practice-panel",
                    "module_url": f"{STATIC_URL}/moon-practice-panel.js?v={FRONTEND_VERSION}",
                    "embed_iframe": False,
                    "trust_external": False,
                },
            },
        )

    @callback
    def stop(self) -> None:
        if self._unsubscribe_dashboard is not None:
            self._unsubscribe_dashboard()
            self._unsubscribe_dashboard = None
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        existing = self.hass.data.get(frontend.DATA_PANELS, {}).get(self.path)
        if existing is not None and (existing.config or {}).get("tarot_api_entry_id") == self.entry.entry_id:
            frontend.async_remove_panel(self.hass, self.path)
