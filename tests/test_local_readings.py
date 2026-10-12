"""Offline regression checks for local tarot readings and provider draws."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ha_test_support import FakeHass, FakeResponse, install_import_stubs

install_import_stubs()

from custom_components import tarot_api
from custom_components.tarot_api import readings
from custom_components.tarot_api.const import DOMAIN, PROVIDER_EKELEN, PROVIDER_KRATES
from custom_components.tarot_api.sensor import TarotCardSensor

ROOT = Path(__file__).resolve().parents[1]
DATASET = json.loads((ROOT / "custom_components/tarot_api/readings.json").read_text(encoding="utf-8"))
RAW_VARIANTS = {"ar08": "Fortitude", "ar10": "Wheel Of Fortune", "ar20": "The Last Judgment"}


def entry(entry_id="test", provider=PROVIDER_EKELEN):
    return SimpleNamespace(entry_id=entry_id, unique_id=entry_id, data={"provider": provider})


def raw_card(card_id, provider=PROVIDER_EKELEN):
    raw = {
        "name": RAW_VARIANTS.get(card_id, DATASET["cards"][card_id]["name"]),
        "desc": "API picture description",
        "meaning_up": "API upright text",
        "meaning_rev": "API reversed text",
        "image_url": "https://example.invalid/card.jpg",
        "_provider": provider,
    }
    if provider == PROVIDER_KRATES:
        raw["name"] = DATASET["cards"][card_id]["name"]
    else:
        raw.update(name_short=card_id, type="major" if card_id.startswith("ar") else "minor", value="4")
    return raw


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = readings.load_readings()

    def test_both_providers_and_all_orientations_preserve_legacy_attributes(self):
        for provider in (PROVIDER_EKELEN, PROVIDER_KRATES):
            hub = tarot_api.TarotHub(FakeHass(), "test", "https://example.invalid", provider, readings=self.catalog)
            sensor = TarotCardSensor(entry(provider=provider), hub)
            for card_id, card in DATASET["cards"].items():
                for orientation in ("upright", "reversed"):
                    with self.subTest(provider=provider, card=card_id, orientation=orientation):
                        hub.last_card, hub.orientation = raw_card(card_id, provider), orientation
                        with patch("pathlib.Path.open", side_effect=AssertionError("Entity property performed disk I/O")):
                            attrs = sensor.extra_state_attributes
                        expected = card[orientation]
                        for field in ("keywords", "interpretation", "reflection"):
                            self.assertEqual(attrs[field], expected[field])
                        self.assertEqual(attrs["card_name"], card["name"])
                        self.assertTrue(attrs["reading_available"])
                        self.assertEqual(attrs["orientation"], orientation)
                        self.assertEqual(attrs["meaning"], f"API {orientation} text")
                        self.assertEqual(attrs["meaning_up"], "API upright text")
                        self.assertEqual(attrs["meaning_rev"], "API reversed text")
                        self.assertEqual(attrs["description"], "API picture description")
                        self.assertEqual(attrs["image_url"], "https://example.invalid/card.jpg")
                        self.assertEqual(sensor.native_value, hub.last_card["name"] + (" (reversed)" if orientation == "reversed" else ""))
                        if provider == PROVIDER_EKELEN:
                            self.assertEqual(attrs["name_short"], card_id)
                            self.assertEqual(attrs["type"], hub.last_card["type"])
                            self.assertEqual(attrs["value"], "4")
                        else:
                            self.assertNotIn("name_short", attrs)

    def test_raw_default_id_takes_precedence_over_name(self):
        raw = raw_card("ar08")
        raw["name"] = "Justice"
        attrs = self.catalog.attributes_for(raw, PROVIDER_EKELEN, "upright")
        self.assertEqual(attrs["card_name"], "Strength")
        self.assertEqual(attrs["interpretation"], DATASET["cards"]["ar08"]["upright"]["interpretation"])

    def test_krates_name_variations(self):
        cases = {
            "  THE   STRENGTH  ": "ar08", "Fortitude": "ar08",
            "Wheel Of Fortune": "ar10", "The Wheel of Fortune": "ar10",
            "Judgment": "ar20", "The Judgement": "ar20",
            "The Last Judgment": "ar20", "Last Judgement": "ar20",
            "Ｆｏｕｒ ｏｆ Ｐｅｎｔａｃｌｅｓ": "pe04",
        }
        for name, card_id in cases.items():
            with self.subTest(name=name):
                attrs = self.catalog.attributes_for({"name": name}, PROVIDER_KRATES, "reversed")
                self.assertEqual(attrs["interpretation"], DATASET["cards"][card_id]["reversed"]["interpretation"])
                self.assertEqual(attrs["card_name"], DATASET["cards"][card_id]["name"])

    def test_unknown_card_clears_previous_reading(self):
        hub = tarot_api.TarotHub(FakeHass(), "test", "https://example.invalid", PROVIDER_EKELEN, readings=self.catalog)
        sensor = TarotCardSensor(entry(), hub)
        self.assertEqual(sensor.extra_state_attributes, {})
        self.assertIsNone(sensor.native_value)
        hub.last_card, hub.orientation = raw_card("pe04"), "reversed"
        self.assertTrue(sensor.extra_state_attributes["reading_available"])
        hub.last_card["name_short"] = "unknown"
        hub.last_card["name"] = "  New card  "
        attrs = sensor.extra_state_attributes
        self.assertEqual(attrs["card_name"], "New card")
        self.assertEqual(attrs["keywords"], [])
        self.assertIsNone(attrs["interpretation"])
        self.assertIsNone(attrs["reflection"])
        self.assertFalse(attrs["reading_available"])
        self.assertEqual(attrs["image_url"], "https://example.invalid/card.jpg")
        self.assertEqual(attrs["meaning"], "API reversed text")

    def test_missing_orientation_never_uses_other_orientation(self):
        cards = deepcopy(self.catalog.cards)
        del cards["pe04"]["reversed"]
        catalog = readings.ReadingCatalog(cards, self.catalog.name_index)
        attrs = catalog.attributes_for(raw_card("pe04"), PROVIDER_EKELEN, "reversed")
        self.assertEqual(attrs["card_name"], "Four of Pentacles")
        self.assertFalse(attrs["reading_available"])
        self.assertIsNone(attrs["interpretation"])
        self.assertFalse(self.catalog.attributes_for(raw_card("pe04"), PROVIDER_EKELEN, "invalid")["reading_available"])

    def test_attributes_do_not_allow_keywords_to_mutate_catalog(self):
        attrs = self.catalog.attributes_for(raw_card("pe04"), PROVIDER_EKELEN, "upright")
        attrs["keywords"].clear()
        self.assertEqual(len(self.catalog.cards["pe04"]["upright"]["keywords"]), 3)

    def test_invalid_or_missing_files_return_unavailable_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(readings, "__file__", str(root / "readings.py")):
                for content in (None, "{", "[]", '{"schema_version":1,"schema_version":1}', "\ufeff{}"):
                    with self.subTest(content=content):
                        path = root / "readings.json"
                        if content is not None:
                            path.write_text(content, encoding="utf-8")
                        with self.assertLogs(readings.__name__, level="WARNING"):
                            catalog = readings.load_readings()
                        self.assertEqual(catalog.cards, {})
                        self.assertFalse(catalog.attributes_for(raw_card("pe04"), PROVIDER_EKELEN, "reversed")["reading_available"])

    def test_incomplete_or_ambiguous_catalog_is_rejected(self):
        mutations = (
            lambda d: d.update(schema_version=True),
            lambda d: d["cards"].pop("ar08"),
            lambda d: d["cards"]["pe04"].pop("reversed"),
            lambda d: d["cards"]["pe04"]["upright"].update(keywords=["a", "a", "b"]),
            lambda d: d["cards"]["ar11"].update(name="Strength"),
        )
        for mutate in mutations:
            data = deepcopy(DATASET)
            mutate(data)
            with self.assertRaises(ValueError):
                readings._parse_catalog(data)


class AsyncIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_setups_load_once_outside_event_loop(self):
        hass, main_thread = FakeHass(), threading.get_ident()
        actual_loader = readings.load_readings

        def checked_loader():
            self.assertNotEqual(threading.get_ident(), main_thread)
            return actual_loader()

        with patch.object(readings, "load_readings", side_effect=checked_loader) as load:
            catalogs = await asyncio.gather(*(readings.async_get_readings(hass) for _ in range(20)))
            self.assertEqual(load.call_count, 1)
        self.assertEqual(hass.executor_jobs, 1)
        self.assertTrue(all(c is catalogs[0] for c in catalogs))
        self.assertEqual(len(catalogs[0].cards), 78)

    async def test_cancelled_waiter_does_not_cancel_shared_load(self):
        hass, started, release = FakeHass(), threading.Event(), threading.Event()
        actual_loader = readings.load_readings

        def delayed_loader():
            started.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release executor")
            return actual_loader()

        with patch.object(readings, "load_readings", side_effect=delayed_loader):
            cancelled = asyncio.create_task(readings.async_get_readings(hass))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                cancelled.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await cancelled
            finally:
                release.set()
            catalog = await readings.async_get_readings(hass)
        self.assertEqual(len(catalog.cards), 78)
        self.assertEqual(hass.executor_jobs, 1)

    async def test_unavailable_catalog_is_cached_and_logged_once(self):
        hass = FakeHass()
        with patch("pathlib.Path.open", side_effect=FileNotFoundError("missing catalog")):
            with self.assertLogs(readings.__name__, level="WARNING") as captured:
                catalogs = await asyncio.gather(*(readings.async_get_readings(hass) for _ in range(5)))
                again = await readings.async_get_readings(hass)
        self.assertEqual(len(captured.output), 1)
        self.assertEqual(hass.executor_jobs, 1)
        self.assertTrue(all(c is again for c in catalogs))
        self.assertEqual(again.cards, {})

    async def test_setup_and_reload_share_catalog_without_network_requests(self):
        hass = FakeHass()
        first, second = entry("first"), entry("second", PROVIDER_KRATES)
        with patch.object(tarot_api, "async_get_clientsession") as get_session:
            await asyncio.gather(tarot_api.async_setup_entry(hass, first), tarot_api.async_setup_entry(hass, second))
            first_catalog = hass.data[DOMAIN]["first"].readings
            self.assertIs(first_catalog, hass.data[DOMAIN]["second"].readings)
            self.assertTrue(await tarot_api.async_unload_entry(hass, first))
            self.assertNotIn("first", hass.data[DOMAIN])
            await tarot_api.async_setup_entry(hass, first)
            self.assertIs(first_catalog, hass.data[DOMAIN]["first"].readings)
            get_session.assert_not_called()
        self.assertEqual(hass.executor_jobs, 1)
        self.assertEqual(hass.config_entries.async_forward_entry_setups.await_count, 3)

    async def test_provider_draws_make_one_request_and_keep_selected_orientation(self):
        catalog = readings.load_readings()
        for provider in (PROVIDER_EKELEN, PROVIDER_KRATES):
            for orientation in ("upright", "reversed"):
                with self.subTest(provider=provider, orientation=orientation):
                    hass = FakeHass()
                    hub = tarot_api.TarotHub(hass, "draw", "https://example.invalid", provider, readings=catalog)
                    if provider == PROVIDER_EKELEN:
                        payload = {"cards": [raw_card("pe04")]}
                        expected_url = "https://example.invalid/api/v1/cards/random?n=1"
                    else:
                        payload = {"name": "  The Four of Pentacles  ", "description": "API description", "image": "/tarotdeck/four.jpeg"}
                        expected_url = "https://example.invalid/cards/onecard"
                    session = SimpleNamespace(get=Mock(return_value=FakeResponse(payload)))
                    with patch.object(tarot_api, "async_get_clientsession", return_value=session), patch.object(tarot_api.random, "choice", return_value=orientation) as choose, patch.object(tarot_api, "async_dispatcher_send") as dispatch:
                        await hub.async_draw_one()
                        attrs = TarotCardSensor(entry(), hub).extra_state_attributes
                    session.get.assert_called_once()
                    self.assertEqual(session.get.call_args.args[0], expected_url)
                    choose.assert_called_once_with(["upright", "reversed"])
                    dispatch.assert_called_once()
                    self.assertEqual(hub.orientation, orientation)
                    self.assertEqual(attrs["interpretation"], DATASET["cards"]["pe04"][orientation]["interpretation"])
                    self.assertTrue(attrs["reading_available"])
                    self.assertTrue(attrs["image_url"])


if __name__ == "__main__":
    unittest.main()
