# Offline tarot integration checks

Install the test-only template parsers into your test environment:

```text
python -m pip install aiohttp PyYAML Jinja2
python -m unittest discover -s tests -v
```

The suite tests both providers across all 156 readings, legacy attribute preservation, name variants, unavailable readings, one shared executor load, setup cancellation, reloads, one request per draw, and dashboard rendering. If Home Assistant is absent, minimal import stubs allow the real integration modules to load. The asynchronous harness provides the documented executor and config-entry interfaces; this is not a running Home Assistant instance.

Artwork tests additionally check all 156 original PNG hashes, exact deck coverage, canonical mapping for both providers, daylight/nighttime selection, solar event subscriptions and cleanup, unchanged draw/orientation on switching, off-event-loop image reads, cache invalidation, sensor proxy URLs, and unavailable-artwork fallback. Include the bundled artwork directories when running these tests.

Dashboard preservation is compared with the pre-task snapshot when available. In a normal checkout that snapshot is absent, so only that check is skipped. All other dashboard checks run normally. PyYAML and Jinja2 are testing tools and are not integration requirements.

Practice tests cover collection completeness, the canonical 24 rune symbols, stable daily selections, full-cycle coverage, local midnight (including UTC/local date disagreement), isolated redraws, restart restoration, invalid/old storage, entry isolation, concurrent draws, failed writes, writes crossing midnight, entity data isolation, timer cleanup, and failed setup cleanup. The asynchronous tests require the event loop's local wake-up socket to be permitted. They use import stubs, not a live HA server.

Frontend checks in PowerShell: `Get-Content -Raw custom_components/tarot_api/frontend/moon-practice-card.js | node --check --input-type=module` and `Get-Content -Raw custom_components/tarot_api/frontend/moon-practice-panel.js | node --check --input-type=module`. Serve the repository and open `examples/moon_practice_preview.html` for browser verification of all five tabs, draw buttons, bundled Tarot art, keyboard navigation, and narrow phone layouts. Append `?panel=1` to check the sidebar wrapper, menu event and renamed entity mappings. Backend tests cover route registration, registry changes, concurrent entries and setup/unload cleanup using HA import stubs. These checks do not validate installation on a live Home Assistant instance.
