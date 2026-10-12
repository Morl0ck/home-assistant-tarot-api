# Offline tarot integration checks

Install the test-only template parsers into your test environment:

```text
python -m pip install aiohttp PyYAML Jinja2
python -m unittest discover -s tests -v
```

The suite tests both providers across all 156 readings, legacy attribute preservation, name variants, unavailable readings, one shared executor load, setup cancellation, reloads, one request per draw, and dashboard rendering. If Home Assistant is absent, minimal import stubs allow the real integration modules to load. The asynchronous harness provides the documented executor and config-entry interfaces; this is not a running Home Assistant instance.

Artwork tests additionally check all 156 original PNG hashes, exact deck coverage, canonical mapping for both providers, daylight/nighttime selection, solar event subscriptions and cleanup, unchanged draw/orientation on switching, off-event-loop image reads, cache invalidation, sensor proxy URLs, and unavailable-artwork fallback. Include the bundled artwork directories when running these tests.

Dashboard preservation is compared with the pre-task snapshot when available. In a normal checkout that snapshot is absent, so only that check is skipped. All other dashboard checks run normally. PyYAML and Jinja2 are testing tools and are not integration requirements.
