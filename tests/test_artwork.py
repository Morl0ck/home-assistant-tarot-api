"""Offline artwork coverage, proxy serving, cache and solar-change checks."""
import asyncio
import hashlib
import json
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ha_test_support import FakeHass, install_import_stubs

install_import_stubs()
from custom_components.tarot_api import TarotHub, artwork
from custom_components.tarot_api.const import PROVIDER_EKELEN, PROVIDER_KRATES
from custom_components.tarot_api.image import TarotCardImage
from custom_components.tarot_api.readings import load_readings
from custom_components.tarot_api.sensor import TarotCardSensor


class ArtworkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = FakeHass()
        self.sun = SimpleNamespace(state="above_horizon")
        self.hass.states.get = lambda entity_id: self.sun
        self.hub = TarotHub(self.hass, "test", "https://example.invalid", PROVIDER_EKELEN, readings=load_readings())
        self.hub.last_card = {"name_short": "ar03", "name": "The Empress", "image_url": "https://example.invalid/card.jpg"}
        self.hub.orientation = "reversed"
        self.entry = SimpleNamespace(entry_id="test", unique_id="test")
        self.face = TarotCardImage(self.hass, self.entry, self.hub)
        self.face.entity_id = "image.test"

    def test_exact_deck_coverage_and_source_integrity(self):
        index = json.loads((artwork.ARTWORK_ROOT / "index.json").read_text())
        for theme in (artwork.DAY_THEME, artwork.NIGHT_THEME):
            rows = index["themes"][theme]
            self.assertEqual(set(rows), artwork.CARD_IDS)
            self.assertEqual({p.stem for p in (artwork.ARTWORK_ROOT / theme).glob("*.png")}, artwork.CARD_IDS)
            for card_id, record in rows.items():
                content = (artwork.ARTWORK_ROOT / theme / f"{card_id}.png").read_bytes()
                self.assertEqual(len(content), record["bytes"])
                self.assertEqual(hashlib.sha256(content).hexdigest(), record["sha256"])

    def test_all_provider_cards_and_known_aliases_resolve(self):
        for provider in (PROVIDER_EKELEN, PROVIDER_KRATES):
            self.hub.provider = provider
            for card_id, row in self.hub.readings.cards.items():
                self.hub.last_card = {"name_short": card_id, "name": row["name"]}
                self.assertEqual(artwork.card_id_for(self.hub), card_id)
        for name, card_id in {"Fortitude": "ar08", "Last Judgment": "ar20"}.items():
            self.hub.last_card = {"name": name}
            self.assertEqual(artwork.card_id_for(self.hub), card_id)
        self.hub.provider = PROVIDER_EKELEN
        self.hub.last_card = {"name_short": "../../readings"}
        self.assertIsNone(artwork.card_id_for(self.hub))

    async def test_original_bytes_cached_off_loop_and_switch_without_redraw(self):
        main_thread = threading.get_ident()
        actual_read = Path.read_bytes
        def checked_read(path):
            self.assertNotEqual(threading.get_ident(), main_thread)
            return actual_read(path)
        with patch.object(Path, "read_bytes", checked_read):
            day = await self.face.async_image()
            self.assertEqual(day, await self.face.async_image())
            self.assertEqual(self.hass.executor_jobs, 1)
            before = self.face._attr_image_last_updated
            self.sun.state = "below_horizon"
            night = await self.face.async_image()
        self.assertNotEqual(day, night)
        self.assertEqual(self.hass.executor_jobs, 2)
        self.assertGreater(self.face._attr_image_last_updated, before)
        self.assertEqual(self.face.artwork_theme, artwork.NIGHT_THEME)
        self.assertEqual(self.hub.orientation, "reversed")
        self.assertEqual(self.hub.last_card["name_short"], "ar03")
        sensor = TarotCardSensor(self.entry, self.hub)
        self.assertEqual(sensor.entity_picture, self.face.entity_picture)
        self.assertEqual(sensor.extra_state_attributes["artwork_url"], self.face.entity_picture)
        self.assertTrue(sensor.extra_state_attributes["reading_available"])

    async def test_solar_listener_notifies_entities_only_on_change_and_unsubscribes(self):
        listeners = {}
        removed = []
        def tracker(hass, ids, callback):
            listeners["sun"] = callback
            return lambda: removed.append("sun")
        def timer(hass, callback, interval):
            listeners["timer"] = callback
            self.assertEqual(interval.total_seconds(), 60)
            return lambda: removed.append("timer")
        with patch("custom_components.tarot_api.image.async_track_state_change_event", tracker), patch("custom_components.tarot_api.image.async_track_time_interval", timer), patch("custom_components.tarot_api.image.async_dispatcher_send") as send:
            await self.face.async_added_to_hass()
            listeners["sun"](None)
            send.assert_not_called()
            self.sun.state = "below_horizon"
            listeners["sun"](None)
            send.assert_called_once()
            listeners["timer"](None)
            send.assert_called_once()
        for remove in self.face.removers:
            if remove:
                remove()
        self.assertEqual(removed, ["sun", "timer"])

    def test_missing_sun_uses_home_location_calculation(self):
        self.sun = None
        with patch.object(artwork, "is_up", return_value=True):
            self.assertEqual(artwork.current_theme(self.hass), artwork.DAY_THEME)
        with patch.object(artwork, "is_up", return_value=False):
            self.assertEqual(artwork.current_theme(self.hass), artwork.NIGHT_THEME)
        self.sun = SimpleNamespace(state="unavailable")
        with patch.object(artwork, "is_up", side_effect=ValueError("No solar events")):
            self.assertEqual(artwork.current_theme(self.hass), artwork.NIGHT_THEME)

    async def test_unknown_or_missing_artwork_falls_back_without_stale_image(self):
        await self.face.async_image()
        self.hub.last_card = {"name_short": "unknown", "image_url": "https://example.invalid/unknown.jpg"}
        self.assertEqual(await self.face.async_image(), b"provider image")
        self.assertIsNone(self.face.artwork_theme)
        self.hub.last_card["name_short"] = "ar04"
        with patch.object(Path, "read_bytes", side_effect=FileNotFoundError("Missing artwork")):
            with self.assertLogs("custom_components.tarot_api.image", level="WARNING"):
                self.assertEqual(await self.face.async_image(), b"provider image")
            self.assertEqual(await self.face.async_image(), b"provider image")
