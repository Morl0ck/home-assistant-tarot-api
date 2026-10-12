"""Daily selection, persistence, entry isolation, and lifecycle regression checks."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ha_test_support import FakeHass, install_import_stubs

install_import_stubs()

from custom_components import tarot_api
from custom_components.tarot_api import practice
from custom_components.tarot_api.button import PracticeDrawButton
from custom_components.tarot_api.sensor import PracticeSensor


class CatalogTests(unittest.TestCase):
    def test_complete_original_collections_and_canonical_runes(self):
        catalog = practice.load_practices()
        self.assertEqual({k: len(v) for k, v in catalog.items()},
                         {"affirmation": 32, "oracle": 18, "deity": 12, "rune": 24})
        self.assertEqual({r["symbol"] for r in catalog["rune"]}, set("ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ"))
        self.assertEqual({r["tradition"] for r in catalog["deity"]}, {"Greek", "Norse", "Egyptian"})
        for deity in catalog["deity"]:
            self.assertTrue(deity["lore"].strip())
            self.assertTrue(deity["source"].startswith("https://"))
        for kind, records in catalog.items():
            self.assertEqual(len({r["id"] for r in records}), len(records), kind)
            for record in records:
                self.assertLessEqual(len(record["name"]), 255)
                for key in ("interpretation", "reflection", "practice"):
                    self.assertTrue(record[key].strip())

    def test_unavailable_catalog_is_logged_and_does_not_raise(self):
        with patch.object(Path, "read_text", side_effect=OSError("missing")), self.assertLogs(practice.__name__, level="WARNING"):
            self.assertEqual(practice.load_practices(), {})


class PracticeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 10, 12, 23, 59, tzinfo=timezone(timedelta(hours=-4)))
        self.clock = patch.object(practice.dt_util, "now", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.hass = FakeHass()
        self.hub = practice.PracticeHub(self.hass, "first", practice.load_practices())
        await self.hub.async_start()
        self.addCleanup(self.hub.stop)

    async def test_daily_choices_are_stable_complete_and_cover_every_item(self):
        for kind, records in self.hub.catalog.items():
            ids = []
            original_date = self.hub.date
            for offset in range(len(records)):
                self.hub.date = original_date + timedelta(days=offset)
                current = self.hub.current(kind)
                self.assertEqual(current, self.hub.current(kind))
                self.assertEqual(current["date"], self.hub.date.isoformat())
                ids.append(current["id"])
            self.assertEqual(len(set(ids)), len(records))
            self.hub.date = original_date

    async def test_manual_draw_does_not_repeat_and_survives_restart(self):
        original = {kind: self.hub.current(kind) for kind in practice.PRACTICES}
        for kind in practice.PRACTICES:
            await self.hub.async_draw(kind)
            self.assertNotEqual(self.hub.current(kind)["id"], original[kind]["id"])
        restored = practice.PracticeHub(self.hass, "first", practice.load_practices())
        await restored.async_start()
        self.addCleanup(restored.stop)
        for kind in practice.PRACTICES:
            self.assertEqual(restored.current(kind), self.hub.current(kind))

    async def test_redrawing_one_category_does_not_change_others(self):
        before = {kind: self.hub.current(kind) for kind in practice.PRACTICES}
        await self.hub.async_draw("oracle")
        for kind in ("affirmation", "deity", "rune"):
            self.assertEqual(before[kind], self.hub.current(kind))

    async def test_midnight_uses_local_day_and_clears_all_overrides(self):
        await self.hub.async_draw("rune")
        self.assertTrue(self.hub.selections)
        # UTC is already October 13, but HA's configured local date is still 12.
        self.hub._tick(self.now.astimezone(timezone.utc))
        self.assertEqual(self.hub.date.isoformat(), "2026-10-12")
        self.now += timedelta(minutes=2)
        with patch.object(practice, "async_dispatcher_send") as dispatch:
            self.hub._tick(self.now.astimezone(timezone.utc))
            self.hub._tick(self.now.astimezone(timezone.utc))
            dispatch.assert_called_once_with(self.hass, practice.SIGNAL_PRACTICE_UPDATED, {"entry_id": "first"})
        self.assertEqual(self.hub.selections, {})
        self.assertEqual(self.hub.current("rune")["date"], "2026-10-13")

    async def test_failed_storage_write_keeps_current_choice(self):
        before = self.hub.current("rune")
        with patch.object(self.hub._store, "async_save", side_effect=OSError("disk full")), patch.object(practice, "async_dispatcher_send") as dispatch:
            with self.assertRaises(OSError):
                await self.hub.async_draw("rune")
            dispatch.assert_not_called()
        self.assertEqual(before, self.hub.current("rune"))

    async def test_slow_write_crossing_midnight_does_not_override_new_day(self):
        async def slow_save(data):
            self.now += timedelta(minutes=2)
        with patch.object(self.hub._store, "async_save", side_effect=slow_save):
            await self.hub.async_draw("rune")
        self.assertEqual(self.hub.selections, {})
        self.assertEqual(self.hub.current("rune")["date"], "2026-10-13")

    async def test_concurrent_draws_keep_all_categories_in_storage(self):
        await asyncio.gather(*(self.hub.async_draw(kind) for kind in practice.PRACTICES))
        self.assertEqual(set(self.hub.selections), set(practice.PRACTICES))
        saved = await self.hub._store.async_load()
        self.assertEqual(saved["selections"], self.hub.selections)

    async def test_entries_are_isolated_and_old_or_invalid_storage_is_ignored(self):
        await self.hub.async_draw("rune")
        second = practice.PracticeHub(self.hass, "second", practice.load_practices())
        await second.async_start()
        self.addCleanup(second.stop)
        self.assertEqual(second.selections, {})
        await second._store.async_save({"date": self.now.date().isoformat(), "selections": {"rune": "not-a-rune", "garbage": "foo"}})
        second.stop()
        await second.async_start()
        self.assertEqual(second.selections, {})
        await second._store.async_save({"date": "2000-01-01", "selections": deepcopy(self.hub.selections)})
        second.stop()
        await second.async_start()
        self.assertEqual(second.selections, {})

    async def test_sensor_attributes_are_isolated_and_buttons_use_local_hub(self):
        entry = SimpleNamespace(entry_id="first", unique_id="unique-first")
        hub = SimpleNamespace(practice=self.hub)
        sensor = PracticeSensor(entry, hub, "oracle")
        self.assertTrue(sensor.available)
        attrs = sensor.extra_state_attributes
        attrs["keywords"].clear()
        self.assertTrue(sensor.extra_state_attributes["keywords"])
        self.assertEqual(sensor.native_value, self.hub.current("oracle")["name"])
        before = sensor.native_value
        await PracticeDrawButton(entry, hub, "oracle").async_press()
        self.assertNotEqual(sensor.native_value, before)
        unavailable = practice.PracticeHub(self.hass, "empty", {})
        sensor = PracticeSensor(entry, SimpleNamespace(practice=unavailable), "oracle")
        self.assertFalse(sensor.available)
        self.assertIsNone(sensor.native_value)

    async def test_interval_is_removed_on_stop(self):
        remove = Mock()
        with patch.object(practice, "async_track_time_interval", return_value=remove) as track:
            hub = practice.PracticeHub(self.hass, "third", practice.load_practices())
            await hub.async_start()
            self.assertEqual(track.call_args.args[2], timedelta(minutes=1))
            hub.stop()
            hub.stop()
            remove.assert_called_once()

    async def test_setup_failure_cleans_up_timer_and_hub(self):
        entry = SimpleNamespace(entry_id="failed", unique_id="failed", data={})
        self.hass.config_entries.async_forward_entry_setups = AsyncMock(side_effect=RuntimeError("failed platform"))
        with patch.object(practice, "async_track_time_interval", return_value=Mock()) as track:
            with self.assertRaises(RuntimeError):
                await tarot_api.async_setup_entry(self.hass, entry)
            track.return_value.assert_called_once()
        self.assertNotIn("failed", self.hass.data[tarot_api.DOMAIN])


if __name__ == "__main__":
    unittest.main()
