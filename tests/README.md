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

Frontend syntax checks: `node --check custom_components/tarot_api/frontend/moon-practice-card.js` and `node --check custom_components/tarot_api/frontend/moon-practice-panel.js`. Run `node tests/test_dashboard_setup.mjs` to check native dashboard creation, permissions, preservation of edits, concurrent creation and failed saves through simulated HA WebSocket APIs.

Horoscope tests cover twelve-sign caching, restart recovery without new requests, partial failures retaining earlier readings, per-sign retries, local midnight, provider-date preservation, malformed responses, manual cooldown, corrupt storage, failed writes, entity attributes and cancellation on unload. These tests use simulated API responses, not the live provider.

Optional browser checks require Playwright with Chromium: `node tests/test_practice_ui.cjs`. Set `UI_SCREENSHOTS` to an existing output directory to save screenshots. The checks use the actual cards and bundled art with sample states, verifying desktop/phone layout, all six sections, redraws, sign persistence, outage messages, safe text rendering, image loading and keyboard navigation. The preview simulates native navigation; it does not verify a live Home Assistant installation. Serve the repository and open `examples/moon_practice_preview.html` for manual inspection.

Three-card spread tests cover distinct local draws, independently chosen orientations, both configured providers without network use, complete readings, independent single-card state, unavailable catalogs, entity attribute isolation, three separate image proxies, day/night artwork changes without redrawing, image caching, and subscription cleanup. Browser checks also exercise the three-card layout on desktop/phone, Past/Present/Future labels, reversed art, redraws, one/three-mode switching, and escaped spread content.

Artwork regression checks reproduce a new card title retaining the previous image when HA's access token has not rotated. Each card/artwork change now gets a distinct authenticated image URL, stable between changes and different when returning to a previously drawn card. Checks also cover day/night URL changes and unchanged card identity/orientation.

The cross-tab browser audit verifies redraw and automatic entity updates for Affirmations, Oracle, Gods, and Runes, matching their displayed names, readings, and symbols to the new state. It also checks the affirmation landscape's day/night transition and horoscope sign/reading changes on desktop and phone. Only Tarot uses image files; a separate spread test verifies that all three positions change both their authenticated URLs and image bytes after a redraw.
