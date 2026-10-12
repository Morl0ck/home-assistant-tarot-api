"""Minimal import support for offline tests when Home Assistant is absent.

Only import surfaces are stubbed. Catalog loading, hub draws, sensor attribute
selection and dashboard rendering use the real integration code under test.
"""

import asyncio
from enum import Enum
import importlib.util
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock


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
    sys.modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = lambda hass: None
    sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = lambda *args: None
    sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_connect = lambda *args: None
    sys.modules["homeassistant.helpers.entity"].DeviceInfo = dict
    sys.modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object
    sys.modules["homeassistant.components.sensor"].SensorEntity = object

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
        self.config_entries = SimpleNamespace(
            async_forward_entry_setups=AsyncMock(),
            async_unload_platforms=AsyncMock(return_value=True),
        )

    def async_add_executor_job(self, target, *args):
        self.executor_jobs += 1
        return asyncio.get_running_loop().run_in_executor(None, target, *args)


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
