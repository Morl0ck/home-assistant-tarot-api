"""Offline spread selection, independent single draws and artwork lifecycle."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ha_test_support import FakeHass, install_import_stubs
install_import_stubs()
from homeassistant.exceptions import HomeAssistantError
from custom_components import tarot_api
from custom_components.tarot_api.button import TarotSpreadButton
from custom_components.tarot_api.const import PROVIDER_EKELEN, PROVIDER_KRATES
from custom_components.tarot_api.image import TarotCardImage
from custom_components.tarot_api.readings import ReadingCatalog, load_readings
from custom_components.tarot_api.sensor import TarotSpreadSensor


class ThreeCardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass=FakeHass()
        self.hub=tarot_api.TarotHub(self.hass,"spread","https://example.invalid",PROVIDER_EKELEN,readings=load_readings())
        self.entry=SimpleNamespace(entry_id="spread",unique_id="uid")
        self.sensor=TarotSpreadSensor(self.entry,self.hub)

    async def test_three_unique_cards_and_independent_orientations_without_api_calls(self):
        for provider in (PROVIDER_EKELEN,PROVIDER_KRATES):
            self.hub.provider=provider
            with patch.object(tarot_api,"async_get_clientsession",side_effect=AssertionError("Network used")), patch.object(tarot_api.random,"choice",side_effect=["upright","reversed","upright"]), patch.object(tarot_api,"async_dispatcher_send") as dispatch:
                await self.hub.async_draw_three()
            cards=self.sensor.extra_state_attributes["cards"]
            self.assertEqual(len({c["name_short"] for c in cards}),3)
            self.assertEqual([c["orientation"] for c in cards],["upright","reversed","upright"])
            self.assertEqual([c["position"] for c in cards],[1,2,3])
            for card in cards:
                self.assertTrue(card["reading_available"])
                self.assertEqual(card["interpretation"],self.hub.readings.cards[card["name_short"]][card["orientation"]]["interpretation"])
            self.assertEqual(self.sensor.native_value,"3 cards")
            self.assertIsNotNone(self.hub.spread_drawn_at)
            dispatch.assert_called_once_with(self.hass,tarot_api.SIGNAL_CARD_UPDATED,{"entry_id":"spread"})

    async def test_spread_does_not_replace_single_card_or_mutate_shared_catalog(self):
        self.hub.last_card={"name_short":"ar00","name":"The Fool"}
        self.hub.orientation="reversed"
        original=deepcopy(self.hub.readings.cards)
        await TarotSpreadButton(self.entry,self.hub).async_press()
        self.assertEqual(self.hub.last_card["name_short"],"ar00")
        self.assertEqual(self.hub.orientation,"reversed")
        attrs=self.sensor.extra_state_attributes
        attrs["cards"][0]["keywords"].clear()
        attrs["cards"][0]["orientation"]="changed"
        self.assertTrue(self.sensor.extra_state_attributes["cards"][0]["keywords"])
        self.assertNotEqual(self.sensor.extra_state_attributes["cards"][0]["orientation"],"changed")
        self.assertEqual(self.hub.readings.cards,original)

    async def test_single_draw_keeps_the_previous_spread(self):
        await self.hub.async_draw_three()
        spread=deepcopy(self.hub.spread_cards)
        with patch.object(self.hub,"_async_draw_ekelen"):
            await self.hub.async_draw_one()
        self.assertEqual(self.hub.spread_cards,spread)

    async def test_unavailable_catalog_disables_button_and_keeps_previous_spread_on_error(self):
        self.assertIsNone(self.sensor.native_value)
        self.assertEqual(self.sensor.extra_state_attributes["cards"],[])
        await self.hub.async_draw_three()
        previous=deepcopy(self.hub.spread_cards)
        self.hub.readings=ReadingCatalog()
        self.assertFalse(TarotSpreadButton(self.entry,self.hub).available)
        with self.assertRaises(HomeAssistantError): await self.hub.async_draw_three()
        self.assertEqual(self.hub.spread_cards,previous)

    async def test_each_card_has_its_own_proxy_and_day_night_art_without_redrawing(self):
        single=TarotCardImage(self.hass,self.entry,self.hub)
        faces=[TarotCardImage(self.hass,self.entry,self.hub,i) for i in range(3)]
        self.assertIs(self.hub.face_image,single)
        for i,face in enumerate(faces): face.entity_id=f"image.spread_{i+1}"
        await self.hub.async_draw_three()
        original=deepcopy(self.hub.spread_cards)
        with patch.object(Path,"read_bytes",side_effect=AssertionError("Sensor read files")):
            attrs=self.sensor.extra_state_attributes
        self.assertEqual(len({c["artwork_url"] for c in attrs["cards"]}),3)
        self.assertTrue(all(c["artwork_theme"]=="mother_nature" for c in attrs["cards"]))
        day=[await face.async_image() for face in faces]
        self.assertTrue(all(data.startswith(b"\x89PNG") for data in day))
        self.assertEqual(self.hass.executor_jobs,3)
        self.assertEqual(day,[await face.async_image() for face in faces])
        self.assertEqual(self.hass.executor_jobs,3)
        self.hass.states.get=lambda _:SimpleNamespace(state="below_horizon")
        night=[await face.async_image() for face in faces]
        self.assertTrue(all(a!=b for a,b in zip(day,night)))
        self.assertEqual(self.hub.spread_cards,original)
        self.assertTrue(all(c["artwork_theme"]=="purple_goddess" for c in self.sensor.extra_state_attributes["cards"]))
        self.assertTrue(all(a["artwork_url"] != b["artwork_url"] for a,b in zip(attrs["cards"],self.sensor.extra_state_attributes["cards"])))

    async def test_spread_image_subscriptions_are_entry_scoped_and_removed(self):
        callbacks=[]
        removed=[]
        def connect(hass,signal,callback):
            callbacks.append(callback)
            return lambda:removed.append(signal)
        faces=[TarotCardImage(self.hass,self.entry,self.hub,i) for i in range(3)]
        with patch("custom_components.tarot_api.image.async_dispatcher_connect",side_effect=connect):
            for face in faces: await face.async_added_to_hass()
        for callback in callbacks: callback({"entry_id":"other"})
        self.assertTrue(all(face.writes==0 for face in faces))
        for callback in callbacks: callback({"entry_id":"spread"})
        self.assertTrue(all(face.writes==1 for face in faces))
        for face in faces:
            for remove in face.removers:
                if remove:remove()
        self.assertEqual(len(removed),3)

    async def test_redraw_refreshes_artwork_urls_for_all_three_positions(self):
        faces=[TarotCardImage(self.hass,self.entry,self.hub,i) for i in range(3)]
        for i,face in enumerate(faces):face.entity_id=f"image.spread_{i+1}"
        with patch.object(tarot_api.random,"sample",side_effect=[["ar00","ar01","ar02"],["sw03","pequ","cu02"]]):
            await self.hub.async_draw_three()
            previous=self.sensor.extra_state_attributes["cards"]
            before=[await face.async_image() for face in faces]
            await self.hub.async_draw_three()
            current=self.sensor.extra_state_attributes["cards"]
            after=[await face.async_image() for face in faces]
        for old,new,old_bytes,new_bytes in zip(previous,current,before,after):
            self.assertNotEqual(old["artwork_url"],new["artwork_url"])
            self.assertNotEqual(old_bytes,new_bytes)
            self.assertIn("token=test",new["artwork_url"])
            self.assertEqual(new["card_name"],self.hub.readings.cards[new["name_short"]]["name"])


if __name__=="__main__": unittest.main()
