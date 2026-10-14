"""Daily horoscope feed with persistent per-sign caching and bounded retries."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date, timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SIGNAL_HOROSCOPE_UPDATED = f"{DOMAIN}_horoscope_updated"
HOROSCOPE_URL = "https://freehoroscopeapi.com/api/v1/get-horoscope/daily"
SIGNS = ("aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces")
RETRY_INTERVAL = timedelta(hours=1)
MANUAL_INTERVAL = timedelta(minutes=5)


def validate_reading(data: Any, sign: str) -> dict[str, str]:
    """Reject malformed/wrong-sign responses and preserve the provider's date."""
    if not isinstance(data, dict) or data.get("period") != "daily":
        raise ValueError("Invalid daily horoscope response")
    name, text, day = data.get("sign"), data.get("horoscope"), data.get("date")
    if not isinstance(name, str) or name.lower() != sign:
        raise ValueError("Horoscope sign does not match request")
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise ValueError("Horoscope text is missing or too long")
    if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
        raise ValueError("Invalid horoscope date")
    return {"sign": sign, "date": day, "interpretation": text.strip()}


class HoroscopeHub:
    """Non-blocking startup; completed signs are reused until local midnight."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass, self.entry_id = hass, entry_id
        self.readings: dict[str, dict[str, str]] = {}
        self.errors: dict[str, str] = {}
        self.date = dt_util.now().date()
        self._store = Store(hass, 1, f"{DOMAIN}_horoscopes_{entry_id}")
        self._task: asyncio.Task | None = None
        self._unsubscribe = None
        self._next_retry = None
        self._last_attempt = None
        self._stopped = False
        self._lock = asyncio.Lock()

    async def async_start(self) -> None:
        try:
            saved = await self._store.async_load()
            if isinstance(saved, dict) and isinstance(saved.get("readings"), dict):
                for sign in SIGNS:
                    record = saved["readings"].get(sign)
                    if not isinstance(record, dict):
                        continue
                    try:
                        self.readings[sign] = validate_reading({"period": "daily", "sign": sign, "date": record.get("date"), "horoscope": record.get("interpretation")}, sign)
                    except (ValueError, TypeError):
                        continue
        except (OSError, ValueError) as err:
            _LOGGER.warning("Could not restore horoscope cache: %s", err)
        self._unsubscribe = async_track_time_interval(self.hass, self._tick, timedelta(minutes=1))
        self._schedule()

    def stop(self) -> None:
        self._stopped = True
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        if self._task is not None:
            self._task.cancel()

    async def async_stop(self) -> None:
        self.stop()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)

    def _notify(self) -> None:
        if not self._stopped:
            async_dispatcher_send(self.hass, SIGNAL_HOROSCOPE_UPDATED, {"entry_id": self.entry_id})

    @callback
    def _tick(self, _now: Any) -> None:
        today = dt_util.now().date()
        if self.date != today:
            self.date = today
            self._next_retry = None
            self._notify()
        self._schedule()

    def _schedule(self) -> None:
        if self._stopped or (self._task is not None and not self._task.done()):
            return
        if all(self.readings.get(sign, {}).get("date") == self.date.isoformat() for sign in SIGNS):
            return
        if self._next_retry is None or dt_util.now() >= self._next_retry:
            self._task = asyncio.create_task(self.async_refresh())

    @property
    def attributes(self) -> dict[str, Any]:
        today = dt_util.now().date().isoformat()
        return {
            "date": today,
            "readings": {sign: {**deepcopy(record), "stale": record["date"] != today} for sign, record in self.readings.items()},
            "errors": dict(self.errors),
            "source": "Free Horoscope API",
            "source_url": "https://freehoroscopeapi.com/",
        }

    async def async_refresh(self, manual: bool = False) -> None:
        """Fetch only missing/stale signs; serialize refreshes and cool down clicks."""
        async with self._lock:
            if self._stopped:
                return
            now = dt_util.now()
            self.date = now.date()
            if manual and self._last_attempt is not None and now < self._last_attempt + MANUAL_INTERVAL:
                return
            pending = [s for s in SIGNS if self.readings.get(s, {}).get("date") != self.date.isoformat()]
            if not pending:
                return
            self._last_attempt = now
            self._next_retry = now + RETRY_INTERVAL
            session = async_get_clientsession(self.hass)
            limit = asyncio.Semaphore(3)

            async def fetch(sign: str) -> None:
                try:
                    async with limit:
                        async with session.get(HOROSCOPE_URL, params={"sign": sign}, timeout=aiohttp.ClientTimeout(total=15)) as response:
                            response.raise_for_status()
                            payload = await response.json()
                    record = validate_reading(payload.get("data") if isinstance(payload, dict) else None, sign)
                    # Never replace a saved reading with older content.
                    previous = self.readings.get(sign)
                    if previous is None or record["date"] >= previous["date"]:
                        self.readings[sign] = record
                    if record["date"] != dt_util.now().date().isoformat():
                        self.errors[sign] = "Today's reading has not been published yet."
                    else:
                        self.errors.pop(sign, None)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as err:
                    self.errors[sign] = "Latest reading unavailable. We'll try again later."
                    _LOGGER.debug("Horoscope update failed for %s: %s", sign, err)

            await asyncio.gather(*(fetch(sign) for sign in pending))
            try:
                await self._store.async_save({"readings": self.readings})
            except (OSError, ValueError) as err:
                _LOGGER.warning("Could not save horoscope cache: %s", err)
            self._notify()
