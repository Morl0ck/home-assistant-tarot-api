"""Bundled UI setup, registry mapping and lifecycle checks without a live HA."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ha_test_support import FakeHass, install_import_stubs

install_import_stubs()

from custom_components import tarot_api
from custom_components.tarot_api import frontend as ui, practice


def entry(key):
    return SimpleNamespace(entry_id=key, unique_id=f"unique-{key}", data={})


def populate(hass, config_entry):
    hass.registry.add("sensor", tarot_api.DOMAIN, f"{config_entry.unique_id}_horoscope", f"sensor.renamed_{config_entry.entry_id}_horoscope", config_entry.entry_id)
    hass.registry.add("button", tarot_api.DOMAIN, f"{config_entry.unique_id}_horoscope_refresh", f"button.renamed_{config_entry.entry_id}_horoscope", config_entry.entry_id)
    for kind in ("tarot", *practice.PRACTICES):
        for domain, suffix in (
            ("sensor", "card" if kind == "tarot" else f"practice_{kind}"),
            ("button", "draw" if kind == "tarot" else f"practice_draw_{kind}"),
        ):
            hass.registry.add(domain, tarot_api.DOMAIN,
                              f"{config_entry.unique_id}_{suffix}",
                              f"{domain}.renamed_{config_entry.entry_id}_{kind}",
                              config_entry.entry_id)


class FrontendTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = FakeHass()
        self.entry = entry("first")
        populate(self.hass, self.entry)

    def panel(self, manager):
        return self.hass.data[ui.frontend.DATA_PANELS][manager.path]

    async def test_concurrent_entries_and_reload_register_assets_once(self):
        first = ui.PracticeFrontend(self.hass, self.entry)
        second_entry = entry("second")
        populate(self.hass, second_entry)
        second = ui.PracticeFrontend(self.hass, second_entry)
        await asyncio.gather(first.async_start(), second.async_start())
        self.hass.http.async_register_static_paths.assert_awaited_once()
        self.assertEqual(len(self.hass.listeners), 4)
        for manager in (first, second):
            panel = self.panel(manager)
            self.assertFalse(panel.require_admin)
            for kind, config in panel.config["card"].items():
                self.assertEqual(config["entity"], f"sensor.renamed_{manager.entry.entry_id}_{kind}")
                self.assertEqual(config["button"], f"button.renamed_{manager.entry.entry_id}_{kind}")
        first.stop()
        self.assertEqual(len(self.hass.listeners), 2)
        self.assertIsNotNone(self.panel(second))
        await first.async_start()
        self.hass.http.async_register_static_paths.assert_awaited_once()
        first.stop()
        first.stop()
        second.stop()
        self.assertEqual(self.hass.listeners, [])
        self.assertEqual(self.hass.data[ui.frontend.DATA_PANELS], {})

    async def test_route_serves_only_bundled_frontend_and_can_retry_failure(self):
        self.hass.http.async_register_static_paths.side_effect = OSError("route failed")
        with self.assertRaises(OSError):
            await ui.async_register_assets(self.hass)
        self.hass.http.async_register_static_paths.side_effect = None
        await ui.async_register_assets(self.hass)
        config = self.hass.http.async_register_static_paths.call_args.args[0][0]
        self.assertEqual(config.url_path, ui.STATIC_URL)
        self.assertEqual(Path(config.path).resolve(), ui.FRONTEND_ROOT.resolve())
        self.assertFalse(config.cache_headers)
        self.assertTrue((Path(config.path) / "moon-practice-card.js").is_file())
        self.assertFalse((Path(config.path) / "practices.json").is_file())

    async def test_cancelled_waiter_does_not_cancel_shared_registration(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def register(paths):
            started.set()
            await finish.wait()

        self.hass.http.async_register_static_paths.side_effect = register
        waiter = asyncio.create_task(ui.async_register_assets(self.hass))
        await started.wait()
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        finish.set()
        await ui.async_register_assets(self.hass)
        self.hass.http.async_register_static_paths.assert_awaited_once()

    async def test_pre_2024_7_http_compatibility(self):
        self.hass.http = SimpleNamespace(register_static_path=Mock())
        await ui.async_register_assets(self.hass)
        self.hass.http.register_static_path.assert_called_once_with(
            ui.STATIC_URL, str(ui.FRONTEND_ROOT), False
        )

    async def test_registry_rename_and_removal_follow_actual_ids(self):
        manager = ui.PracticeFrontend(self.hass, self.entry)
        await manager.async_start()
        record = self.hass.registry.records[("sensor", tarot_api.DOMAIN, "unique-first_practice_rune")]
        old_id = record.entity_id
        record.entity_id = "sensor.wifes_favourite_rune"
        listener = self.hass.listeners[0][1]
        listener(SimpleNamespace(data={"action":"update", "entity_id":record.entity_id, "old_entity_id":old_id}))
        self.assertEqual(self.panel(manager).config["card"]["rune"]["entity"], record.entity_id)
        del self.hass.registry.records[("sensor", tarot_api.DOMAIN, "unique-first_practice_rune")]
        listener(SimpleNamespace(data={"action":"remove", "entity_id":record.entity_id}))
        self.assertEqual(self.panel(manager).config["card"]["rune"]["entity"], "sensor.tarot_api_missing_rune")
        manager.stop()

    async def test_unrelated_registry_event_does_not_replace_panel(self):
        manager = ui.PracticeFrontend(self.hass, self.entry)
        await manager.async_start()
        panel = self.panel(manager)
        self.hass.listeners[0][1](SimpleNamespace(data={"entity_id":"sensor.unrelated"}))
        self.assertIs(self.panel(manager), panel)
        manager.stop()

    async def test_missing_entities_do_not_use_another_entries_defaults(self):
        manager = ui.PracticeFrontend(self.hass, entry("empty"))
        await manager.async_start()
        for kind, config in self.panel(manager).config["card"].items():
            self.assertEqual(config["entity"], f"sensor.tarot_api_missing_{kind}")
            self.assertEqual(config["button"], f"button.tarot_api_missing_{kind}")
        manager.stop()

    async def test_collision_does_not_overwrite_or_remove_existing_panel(self):
        manager = ui.PracticeFrontend(self.hass, self.entry)
        existing = SimpleNamespace(config={"unrelated":True})
        self.hass.data[ui.frontend.DATA_PANELS] = {manager.path:existing}
        with self.assertRaises(ValueError):
            await manager.async_start()
        manager.stop()
        self.assertIs(self.panel(manager), existing)
        self.assertEqual(self.hass.listeners, [])

    async def test_frontend_setup_failure_unloads_platforms_and_practice_timer(self):
        self.hass.http.async_register_static_paths.side_effect = OSError("route failed")
        with patch.object(practice, "async_track_time_interval", return_value=Mock()) as track:
            with self.assertRaises(OSError):
                await tarot_api.async_setup_entry(self.hass, self.entry)
            track.return_value.assert_called_once()
        self.hass.config_entries.async_unload_platforms.assert_awaited_once()
        self.assertNotIn(self.entry.entry_id, self.hass.data[tarot_api.DOMAIN])
        self.assertEqual(self.hass.listeners, [])

    async def test_integration_unload_and_failed_unload_lifecycle(self):
        await tarot_api.async_setup_entry(self.hass, self.entry)
        manager = self.hass.data[tarot_api.DOMAIN][self.entry.entry_id].frontend
        self.assertIsNotNone(self.panel(manager))
        self.hass.config_entries.async_unload_platforms.return_value = False
        self.assertFalse(await tarot_api.async_unload_entry(self.hass, self.entry))
        self.assertIsNotNone(self.panel(manager))
        self.assertEqual(len(self.hass.listeners), 2)
        self.hass.config_entries.async_unload_platforms.return_value = True
        self.assertTrue(await tarot_api.async_unload_entry(self.hass, self.entry))
        self.assertNotIn(manager.path, self.hass.data[ui.frontend.DATA_PANELS])
        self.assertEqual(self.hass.listeners, [])

    def test_bundle_import_and_manifest_versions_match(self):
        manifest = json.loads((ui.FRONTEND_ROOT.parent / "manifest.json").read_text())
        self.assertEqual(manifest["version"], ui.FRONTEND_VERSION)
        self.assertIn("frontend", manifest["dependencies"])
        panel_source = (ui.FRONTEND_ROOT / "moon-practice-panel.js").read_text(encoding="utf-8")
        self.assertIn(f'"./moon-practice-card.js?v={ui.FRONTEND_VERSION}"', panel_source)

    async def test_native_dashboard_is_never_rewritten_or_removed_on_unload(self):
        manager = ui.PracticeFrontend(self.hass, self.entry)
        await manager.async_start()
        native = SimpleNamespace(component_name="lovelace", config={"mode":"storage", "user_edit":"preserve"})
        self.hass.data[ui.frontend.DATA_PANELS][manager.dashboard_path] = native
        manager._on_dashboard_update(SimpleNamespace(data={"url_path":manager.dashboard_path}))
        self.assertNotIn(manager.path, self.hass.data[ui.frontend.DATA_PANELS])
        manager.stop()
        await manager.async_start()
        self.assertNotIn(manager.path, self.hass.data[ui.frontend.DATA_PANELS])
        self.assertIs(self.hass.data[ui.frontend.DATA_PANELS][manager.dashboard_path], native)
        manager.stop()

    async def test_card_module_is_loaded_globally_once(self):
        await ui.async_register_assets(self.hass)
        await ui.async_register_assets(self.hass)
        self.assertEqual(self.hass.data["test_extra_modules"], {f"{ui.STATIC_URL}/moon-practice-card.js?v={ui.FRONTEND_VERSION}"})


if __name__ == "__main__":
    unittest.main()
