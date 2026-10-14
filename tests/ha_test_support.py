"""Minimal import support for offline tests when Home Assistant is absent.

Only import surfaces are stubbed. Catalog loading, hub draws, sensor attribute
selection and dashboard rendering use the real integration code under test.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
import importlib.util
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock
from dataclasses import dataclass


def install_import_stubs():
    if "homeassistant" in sys.modules or importlib.util.find_spec("homeassistant") is not None:
        return
    for name in (
        "homeassistant", "homeassistant.config_entries", "homeassistant.const",
        "homeassistant.core", "homeassistant.exceptions", "homeassistant.helpers",
        "homeassistant.helpers.aiohttp_client", "homeassistant.helpers.dispatcher",
        "homeassistant.helpers.entity", "homeassistant.helpers.entity_platform",
        "homeassistant.components", "homeassistant.components.sensor",
        "homeassistant.components.image", "homeassistant.helpers.event",
        "homeassistant.helpers.sun",
        "homeassistant.helpers.storage", "homeassistant.util", "homeassistant.util.dt",
        "homeassistant.components.button",
        "homeassistant.components.frontend", "homeassistant.components.http",
        "homeassistant.helpers.entity_registry",
    ):
        module = ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module

    class Platform(str, Enum):
        BUTTON = "button"
        IMAGE = "image"
        SENSOR = "sensor"

    sys.modules["homeassistant.config_entries"].ConfigEntry = object
    sys.modules["homeassistant.const"].Platform = Platform
    sys.modules["homeassistant.core"].HomeAssistant = object
    sys.modules["homeassistant.core"].callback = lambda fn: fn
    sys.modules["homeassistant.exceptions"].HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    sys.modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = lambda hass: SimpleNamespace(get=lambda url, **kwargs: FakeResponse({"data": {"period": "daily", "sign": kwargs.get("params", {}).get("sign", "aries"), "date": sys.modules["homeassistant.util.dt"].now().date().isoformat(), "horoscope": "Sample daily horoscope."}}))
    sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = lambda *args: None
    sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_connect = lambda *args: None
    sys.modules["homeassistant.helpers.entity"].DeviceInfo = dict
    sys.modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object
    sys.modules["homeassistant.components.sensor"].SensorEntity = object
    sys.modules["homeassistant.components.button"].ButtonEntity = object
    sys.modules["homeassistant.util.dt"].now = lambda: datetime.now(timezone.utc)
    sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda hass: hass.registry
    frontend = sys.modules["homeassistant.components.frontend"]
    frontend.DATA_PANELS = "frontend_panels"
    frontend.add_extra_js_url = lambda hass, url: hass.data.setdefault("test_extra_modules", set()).add(url)

    def register_panel(hass, **kwargs):
        panels = hass.data.setdefault(frontend.DATA_PANELS, {})
        path = kwargs["frontend_url_path"]
        if path in panels and not kwargs.get("update"):
            raise ValueError("Panel already exists")
        panels[path] = SimpleNamespace(**kwargs)

    frontend.async_register_built_in_panel = register_panel
    frontend.async_remove_panel = lambda hass, path: hass.data[frontend.DATA_PANELS].pop(path, None)

    @dataclass
    class StaticPathConfig:
        url_path: str
        path: str
        cache_headers: bool

    sys.modules["homeassistant.components.http"].StaticPathConfig = StaticPathConfig

    class Store:
        def __init__(self, hass, version, key):
            self.hass, self.key = hass, key

        async def async_load(self):
            return self.hass.data.get("test_storage", {}).get(self.key)

        async def async_save(self, data):
            self.hass.data.setdefault("test_storage", {})[self.key] = data

    sys.modules["homeassistant.helpers.storage"].Store = Store

    class ImageEntity:
        entity_id = None

        def __init__(self, hass):
            self.hass = hass
            self.removers = []
            self.writes = 0

        @property
        def entity_picture(self):
            return f"/api/image_proxy/{self.entity_id}?token=test"

        async def async_image(self):
            self._attr_content_type = "image/jpeg"
            return b"provider image"

        async def async_added_to_hass(self):
            pass

        def async_on_remove(self, remover):
            self.removers.append(remover)

        def async_write_ha_state(self):
            self.writes += 1

    sys.modules["homeassistant.components.image"].ImageEntity = ImageEntity
    sys.modules["homeassistant.helpers.event"].async_track_state_change_event = lambda *args: lambda: None
    sys.modules["homeassistant.helpers.event"].async_track_time_interval = lambda *args: lambda: None
    sys.modules["homeassistant.helpers.sun"].is_up = lambda hass: True


class FakeHass:
    def __init__(self):
        self.data = {}
        self.states = SimpleNamespace(get=lambda entity_id: SimpleNamespace(state="above_horizon"))
        self.executor_jobs = 0
        self.http = SimpleNamespace(async_register_static_paths=AsyncMock())
        self.registry = FakeRegistry()
        self.listeners = []

        def listen(event_type, listener):
            item = (event_type, listener)
            self.listeners.append(item)
            return lambda: self.listeners.remove(item)

        self.bus = SimpleNamespace(async_listen=listen)
        self.config_entries = SimpleNamespace(
            async_forward_entry_setups=AsyncMock(),
            async_unload_platforms=AsyncMock(return_value=True),
        )

    def async_add_executor_job(self, target, *args):
        self.executor_jobs += 1
        return asyncio.get_running_loop().run_in_executor(None, target, *args)


class FakeRegistry:
    def __init__(self):
        self.records = {}

    def add(self, domain, platform, unique_id, entity_id, entry_id):
        self.records[(domain, platform, unique_id)] = SimpleNamespace(
            entity_id=entity_id, config_entry_id=entry_id
        )

    def async_get_entity_id(self, domain, platform, unique_id):
        record = self.records.get((domain, platform, unique_id))
        return record.entity_id if record else None

    def async_get(self, entity_id):
        return next((r for r in self.records.values() if r.entity_id == entity_id), None)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        return self.payload
