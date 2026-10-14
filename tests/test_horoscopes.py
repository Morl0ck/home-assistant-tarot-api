"""Cache, failure, date and lifecycle checks using the real horoscope manager."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ha_test_support import FakeHass, FakeResponse, install_import_stubs
install_import_stubs()
from custom_components.tarot_api import horoscope as feed
from custom_components.tarot_api.button import HoroscopeRefreshButton
from custom_components.tarot_api.sensor import HoroscopeSensor


class HoroscopeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026,10,14,23,59,tzinfo=timezone(timedelta(hours=-4)))
        self.clock = patch.object(feed.dt_util,"now",side_effect=lambda:self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.hass = FakeHass()
        self.hub = feed.HoroscopeHub(self.hass,"first")
        self.addAsyncCleanup(self.hub.async_stop)
        self.session = SimpleNamespace(get=Mock(side_effect=self.response))
        self.client = patch.object(feed,"async_get_clientsession",return_value=self.session)
        self.client.start()
        self.addCleanup(self.client.stop)

    def response(self,url,**kwargs):
        sign = kwargs["params"]["sign"]
        return FakeResponse({"data":{"sign":sign.title(),"date":self.now.date().isoformat(),"period":"daily","horoscope":f"Reading for {sign}"}})

    async def test_daily_cache_persists_and_manual_refresh_is_request_free_when_complete(self):
        await self.hub.async_start()
        await self.hub._task
        self.assertEqual(self.session.get.call_count,12)
        await self.hub.async_refresh(manual=True)
        self.assertEqual(self.session.get.call_count,12)
        second = feed.HoroscopeHub(self.hass,"first")
        await second.async_start()
        self.addAsyncCleanup(second.async_stop)
        self.assertIsNone(second._task)
        self.assertEqual(second.readings,self.hub.readings)
        self.assertEqual(self.session.get.call_count,12)
        attrs = self.hub.attributes
        attrs["readings"]["aries"]["interpretation"]="changed"
        self.assertNotEqual(attrs,self.hub.attributes)

    async def test_partial_failure_preserves_old_reading_and_retries_only_missing_sign(self):
        self.hub.readings["aries"]={"sign":"aries","date":"2026-10-13","interpretation":"Saved yesterday"}
        def partial(url,**kwargs):
            if kwargs["params"]["sign"]=="aries": raise asyncio.TimeoutError()
            return self.response(url,**kwargs)
        self.session.get.side_effect=partial
        await self.hub.async_refresh()
        self.assertEqual(self.hub.readings["aries"]["interpretation"],"Saved yesterday")
        self.assertTrue(self.hub.attributes["readings"]["aries"]["stale"])
        self.assertEqual(set(self.hub.errors),{"aries"})
        self.now += timedelta(hours=1)
        # Keep successful signs on the same local date for this retry.
        for sign in feed.SIGNS[1:]: self.hub.readings[sign]["date"]=self.now.date().isoformat()
        self.session.get.reset_mock(side_effect=True)
        self.session.get.side_effect=self.response
        await self.hub.async_refresh()
        self.assertEqual(self.session.get.call_count,1)
        self.assertEqual(self.hub.errors,{})

    async def test_midnight_refresh_uses_ha_date_and_dates_from_provider_are_not_relabelled(self):
        await self.hub.async_refresh()
        self.hub._tick(self.now.astimezone(timezone.utc))
        self.assertIsNone(self.hub._task)
        self.now += timedelta(minutes=2)
        self.hub._tick(self.now.astimezone(timezone.utc))
        self.assertTrue(self.hub.attributes["readings"]["aries"]["stale"])
        await self.hub._task
        self.assertEqual(self.session.get.call_count,24)
        self.assertFalse(self.hub.attributes["readings"]["aries"]["stale"])

    async def test_provider_old_date_keeps_saved_newer_reading_and_cooldown_applies(self):
        self.hub.readings["aries"]={"sign":"aries","date":"2026-10-13","interpretation":"Saved"}
        self.session.get.side_effect=lambda url,**kw:FakeResponse({"data":{"period":"daily","sign":kw["params"]["sign"],"date":"2026-10-12","horoscope":"Old"}})
        await self.hub.async_refresh()
        self.assertEqual(self.hub.readings["aries"]["interpretation"],"Saved")
        await asyncio.gather(self.hub.async_refresh(manual=True),self.hub.async_refresh(manual=True))
        self.assertEqual(self.session.get.call_count,12)
        self.hub._tick(self.now)
        self.assertIsNone(self.hub._task)

    async def test_invalid_payloads_never_replace_cache(self):
        for payload in (None,{}, {"data":[]}, {"data":{"period":"daily","sign":"other","date":"2026-10-14","horoscope":"Text"}}):
            self.session.get.return_value=FakeResponse(payload)
            self.session.get.side_effect=None
            await self.hub.async_refresh()
            self.assertEqual(self.hub.readings,{})
            self.assertEqual(len(self.hub.errors),12)

    async def test_corrupt_cache_and_failed_save_do_not_block_current_readings(self):
        await self.hub._store.async_save({"readings":{"aries":{"date":"wrong","interpretation":"Bad"}}})
        with patch.object(self.hub._store,"async_save",side_effect=OSError("disk full")), self.assertLogs(feed.__name__,level="WARNING"):
            await self.hub.async_start()
            await self.hub._task
        self.assertEqual(len(self.hub.readings),12)

    async def test_stop_cancels_inflight_requests_and_removes_timer(self):
        started = asyncio.Event()
        class SlowResponse(FakeResponse):
            async def json(self):
                started.set()
                await asyncio.Event().wait()
        self.session.get.side_effect=lambda *a,**k:SlowResponse({})
        remove=Mock()
        with patch.object(feed,"async_track_time_interval",return_value=remove):
            await self.hub.async_start()
        await started.wait()
        await self.hub.async_stop()
        remove.assert_called_once()
        self.assertTrue(self.hub._task.cancelled())

    async def test_sensor_and_button_use_horoscope_manager(self):
        await self.hub.async_refresh()
        entry=SimpleNamespace(entry_id="first",unique_id="uid")
        hub=SimpleNamespace(horoscope=self.hub)
        sensor=HoroscopeSensor(entry,hub)
        self.assertEqual(sensor.native_value,"2026-10-14")
        self.assertEqual(len(sensor.extra_state_attributes["readings"]),12)
        with patch.object(self.hub,"async_refresh",new_callable=AsyncMock) as refresh:
            await HoroscopeRefreshButton(entry,hub).async_press()
            refresh.assert_awaited_once_with(manual=True)


if __name__ == "__main__": unittest.main()
