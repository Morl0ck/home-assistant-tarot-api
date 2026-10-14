# Tarot API — Home Assistant

Custom integration: draw a random Rider–Waite–Smith card over HTTP, display **Mother Nature artwork by day and Purple Goddess artwork at night**, and read an original bundled upright/reversed interpretation. Includes a native **`image`** entity for Picture cards, a **`sensor`** for the reading, and a **`button`** to draw again.

**Data sources**

- **Default:** [tarotapi.dev](https://tarotapi.dev) ([ekelen/tarot-api](https://github.com/ekelen/tarot-api)) supplies random card metadata. Recognized cards use the bundled artwork; [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json) scan URLs are retained as a fallback. No image server required.
- **Optional:** [krates98/tarotcardapi](https://github.com/krates98/tarotcardapi) on your network; set its base URL in the flow (not `tarotapi.dev`).
- **Readings:** all 156 interpretations are bundled in [`readings.json`](custom_components/tarot_api/readings.json). They load once in a background worker; reading text needs no AI service or additional API request. Providers still supply the random card.
- **Artwork:** two original 78-card decks are bundled locally: Mother Nature by day and Purple Goddess at night. Recognized cards use the original PNGs through Home Assistant's image proxy; external scans are a fallback.

**Requirements:** Home Assistant **2024.11+**, access to your chosen card API, and about **543 MiB** of storage for the artwork. Normal card images and readings load locally. External fallback images need access to their image host; the initial card-back placeholder needs access to Wikimedia.

## Daily Practice dashboard (1.5.0)

Daily Practice now uses **Home Assistant's native dashboard tabs**: **Affirmations, Tarot, Oracle, Gods, Runes, and Horoscopes**. The Sections views use the available desktop width, with artwork or sign selection on the left and reading content on the right. On phones the same content stacks vertically; horoscope signs use a compact dropdown. The lavender palette, moon scenery, and original Tarot artwork remain. No frontend libraries, card-mod, subscription, or AI account are required. The responsive dashboard requires **Home Assistant 2024.11+**.

### Open or upgrade Daily Practice

1. Install the updated integration through HACS or copy the complete `custom_components/tarot_api` directory into Home Assistant, including its `frontend`, catalogs and artwork directories. Restart Home Assistant. New installations also need **Settings → Devices & services → Add integration → Tarot API**.
2. Refresh your browser or Companion app. **An administrator must open Daily Practice once.** Its first-open page creates a normal, editable dashboard using Home Assistant's authenticated dashboard APIs, then opens the Affirmations view. This requires no API key, resource configuration, or pasted YAML. Other users can use the resulting dashboard.
3. Use the native tabs to change practices. Desktop views show two columns; phones show one. Use Home Assistant's dashboard editor to rearrange sections, resize the card, or add your own cards.

The integration loads its card module automatically. The first-open page uses the old `tarot-practice-<entry_id>` route and the native dashboard uses `daily-practice-<entry_id>`. Once the native layout is saved, the old sidebar page disappears. Update old bookmarks to the new dashboard. Each integration entry has its own dashboard and cache. Existing manually configured Lovelace cards continue working, including their internal practice tabs.

**Your dashboard edits are preserved.** Creation only seeds a missing dashboard; reloads and integration updates never overwrite an existing layout. The generated cards resolve entities through the registry, including renamed entities. Removing or unloading the integration leaves the native dashboard in place so your edits survive; remove it separately in **Settings → Dashboards** if you no longer need it. If you delete its cache entity from a card configuration or remove the integration, that card shows an unavailable message.

If the first-open page cannot save the layout, it shows the error and keeps the newly created dashboard. Use the bundled YAML example to populate it manually, or delete the empty dashboard in Settings and retry. Creation honors Home Assistant's administrator permissions. It does not write directly to HA's dashboard storage files.

### Horoscopes with minimal internet use

The Horoscopes view uses [Free Horoscope API](https://freehoroscopeapi.com/), a public daily feed with no account or API key. Select one of the twelve signs; the selection is remembered per browser/device and integration entry. Your zodiac choice stays local and the integration fetches all twelve signs so multiple household members can use different signs.

Readings are saved per entry in HA's `.storage` and restored after restarts. In normal operation each sign is fetched once per day: **12 requests per entry per day**. Browsing, changing signs, opening another dashboard, and restarting with a complete current cache make no horoscope requests. Only missing or stale signs are fetched; successful signs are retained during partial failures. Requests have a 15-second timeout, with at most three in flight. Startup and local midnight updates run in the background and do not block integration setup or the other practices.

Automatic retries occur at most hourly. **Refresh horoscopes** retries missing/stale readings, with a five-minute cooldown; it does not replace an already saved reading for today. In an outage the previous reading remains visible with its original date and a clear message. Before any reading has been saved, the card shows a loading or unavailable message. Provider dates are never relabeled as today's date: a provider publishing on another schedule may display a dated reading until its next update. The source link appears beneath the reading. The feed is externally written horoscope content, not locally calculated planetary positions.

### Bundled practices

The other four collections remain bundled in `practices.json`: **32 affirmations**, **18 original Oracle cards**, **12 mixed Greek/Norse/Egyptian deity cards**, and **24 Elder Futhark runes**. Each includes a modern interpretation, a reflection question, and a small practice. Deity cards also contain mythology profiles and reference URLs in their sensor attributes. These collections need no network requests. Tarot continues to use the chosen card provider, original 78-card decks, and bundled upright/reversed readings.

Affirmations, Oracle, Gods, and Runes automatically rotate through every item before repeating, stay consistent across devices, and refresh within one minute of midnight in **Home Assistant's configured timezone**. Manual draws survive same-day restarts and reset the following day. Tarot retains manual draws and starts without a drawn card after a restart.

### Optional: create your own dashboard or embed a card

The complete native dashboard example is [`examples/moon_practice_dashboard.yaml`](examples/moon_practice_dashboard.yaml). Paste it into a dashboard's **Raw configuration editor**, checking the entity IDs against **Developer tools → States**. For a single Manual card, use a `custom:moon-practice-card` block with `section: horoscope` (or `affirmation`, `tarot`, `oracle`, `deity`, `rune`). Omit `section` to keep the internal tabbed card. `default_tab` selects its initial tab, and `sign: leo` supplies a default zodiac choice when no browser preference has been saved.

The integration registers **`/tarot_api_static/moon-practice-card.js?v=1.5.0`** automatically. Remove or update manually registered older resources to avoid loading an older card first. Generated cards contain `entry_id` and `unique_prefix` to follow registry renames; manually configured cards can use explicit sensor and button mappings.

| Practice | Default sensor | Default button |
|----------|----------------|----------------|
| Affirmations | `sensor.daily_affirmation` | `button.new_affirmation` |
| Tarot | `sensor.tarot_card` | `button.draw_tarot_card` |
| Oracle | `sensor.oracle_card` | `button.draw_oracle_card` |
| Gods | `sensor.deity_card` | `button.draw_deity_card` |
| Runes | `sensor.rune` | `button.draw_rune` |
| Horoscopes | `sensor.daily_horoscope` | `button.refresh_horoscopes` |

The horoscope sensor's state is its latest saved provider date. Attributes include a `readings` dictionary keyed by lowercase sign, each containing `sign`, `date`, `interpretation`, and `stale`; `errors` contains messages for unavailable signs. Sensor text is not truncated to fit the state field.

For a local interactive preview with sample HA states, run `python -m http.server 8766 --bind 127.0.0.1` from the repository root and open `http://127.0.0.1:8766/examples/moon_practice_preview.html`. This exercises the actual cards with simulated native navigation; it is not a live Home Assistant installation. Add `?legacy=1` for the embedded tabbed card, `?tab=horoscope&scenario=horoscope-outage` for saved older readings, or `?tab=horoscope&scenario=horoscope-empty` for an unavailable feed with no cache.

## Daytime and nighttime artwork

Version **1.3.0** switches automatically with `sun.sun`: above the horizon selects **Mother Nature** and below the horizon selects **Purple Goddess**. A sunrise or sunset changes the artwork of the current card without drawing again or changing its orientation or reading. If Sun is absent or unavailable, the configured home location supplies the solar calculation, checked once a minute; if no solar event can be calculated, the nighttime theme is used.

Both decks contain all 78 canonical card IDs. The Purple Goddess title **The Goddess** maps to The Empress (`ar03`); **The Hanged One** maps to The Hanged Man (`ar12`). Readings retain their traditional card names. Both API providers use the same matching rules as the bundled readings.

The existing `image.*` entity and dashboard remain usable. The sensor picture mirrors the image proxy and adds `artwork_theme` and `artwork_url`; its existing `image_url` retains the provider's URL for compatibility. Local images are read in an executor and cached for the current card/theme. Missing or invalid PNGs and unknown cards fall back to provider artwork, with a warning for missing bundled assets.

For a manual update, copy the **entire** `custom_components/tarot_api` folder, including `artwork/mother_nature`, `artwork/purple_goddess`, and `artwork/index.json`, into Home Assistant's `config/custom_components`, then restart Home Assistant and draw a card. There are 156 original 1024 × 1536 PNGs; allow about 543 MiB for the artwork. Local checkout changes take effect in Home Assistant after copying them or installing a published update.

---

## Install

**HACS:** Integrations → menu → **Custom repositories** → URL `https://github.com/Morl0ck/home-assistant-tarot-api`, category **Integration**. Install, restart Home Assistant, then **Settings → Devices & services → Add integration → Tarot API**.

**Manual:** Copy the complete [`custom_components/tarot_api`](custom_components/tarot_api) directory to `config/custom_components/tarot_api`, including `readings.json` and both `artwork` subdirectories. Restart Home Assistant, then add the integration.

**Updating an existing installation:** Install the repository update through HACS, or replace the complete integration directory manually. Restart Home Assistant, refresh the browser or Companion app, and open **Daily Practice** in the sidebar. Draw a Tarot card to populate that tab. Existing entity IDs and dashboards remain compatible; automatic artwork switching needs no extra automation. Confirm the integration's `manifest.json` reports version **1.5.0** and set your home location correctly under Home Assistant's system settings. HACS installs the bundled Practice UI along with the integration.

If HACS errors with **`unexpected character: line 1 column 1`**, it’s usually wrong repo URL (repository root only, not `/tree/main` or raw), JSON saved with a **UTF-8 BOM**, bad HACS storage (`config/.storage/hacs.repositories` — backup, delete while HA stopped, restart), or wrong category (**Integration**). This repo keeps JSON UTF-8 without BOM and LF per [`.gitattributes`](.gitattributes).

---

## Configuration

One config entry is enough.

The provider selects where cards are drawn. Both choices use the bundled readings and automatic daytime/nighttime artwork.

| Flow choice | Meaning |
|-------------|---------|
| tarotapi.dev | Card draws from the public API; optional override of API base URL if you self-host the same API. Readings use the bundled catalog. |
| krates98 | Your server, e.g. `http://192.168.1.10:3000`. |

---

## Entities

One device (e.g. “Tarot draw”): **Draw** button, **Tarot card** sensor, **Tarot card face** image. Check **Developer tools → States** for exact `entity_id`s.

The sensor adds **`card_name`**, **`keywords`**, **`interpretation`**, **`reflection`**, and **`reading_available`** for the current orientation. Existing provider meanings, description, identity attributes, and image URL remain available. The sensor state retains its existing `(reversed)` suffix; use `card_name` for a heading with orientation shown separately.

Default cards match by their raw `name_short`. krates98 cards match by normalized raw names, including optional leading “The,” capitalization/spacing differences, Fortitude/Strength, and Judgment/Judgement/Last Judgment variants. Strength is VIII (`ar08`); Justice is XI (`ar11`). Unknown cards or unavailable readings retain the draw and image, with empty keywords, null interpretation/reflection, and `reading_available: false`.

Picture Entity card **`entity`** must be **`image.…`**, not the sensor — HA only treats camera/image/person as image sources there. Example layout: [`examples/tarot_dashboard_card.yaml`](examples/tarot_dashboard_card.yaml).

The example displays the clean card name and orientation once, then keywords, interpretation, and reflection. It preserves paragraph breaks and shows a brief message if a local reading is unavailable. Copy its updated Markdown card into your actual dashboard and use your entity IDs; editing this repository example does not automatically change a dashboard stored in Home Assistant.

For a custom image template, use the sensor's `artwork_url` for the currently displayed image; `image_url` is the original provider image. The `artwork_theme` values are `mother_nature` and `purple_goddess`, or null when the drawn card is unrecognized.

**Reversed (optional):** `orientation` is on the sensor. With [card-mod](https://github.com/thomasloven/lovelace-card-mod) v4 (Jinja in `style:`):

```yaml
type: picture-entity
entity: image.your_tarot_card_face
card_mod:
  style: |
    ha-card {
      {% if state_attr('sensor.your_tarot_card', 'orientation') == 'reversed' %}
      transform: rotate(180deg);
      {% endif %}
    }
```

---

## Ops notes

| Symptom | Check |
|---------|--------|
| Setup fails | Logs; full `tarot_api` tree under `custom_components`; restart after changes. |
| Picture card empty / wrong | `entity` is **`image.*`**, not `sensor.*`. |
| No artwork | Copy both bundled artwork directories with the integration; verify API access. External fallback images require access to the provider image host. |
| Theme stays on day or night | Check `sun.sun` and your configured home location. Without an available Sun entity, allow up to one minute for the location-based check. |
| Old scans still appear | Restart after updating, draw a card, and confirm both artwork directories are installed. Check logs for missing or invalid bundled PNGs. |
| Local reading unavailable | Check logs and ensure `readings.json` was copied with the integration. After repairing the file, restart HA to reload the shared catalog. |

**Publishing your own fork:** [`scripts/publish-github.ps1`](scripts/publish-github.ps1) — `gh auth login`, then run from repo root (adjust `$RepoName` if needed). Or `gh repo create … --source=. --push` and align `manifest.json` URLs.

---

## Credits

Card metadata / original API text: [ekelen/tarot-api](https://github.com/ekelen/tarot-api). Bundled readings: original traditional, warm, reflective interpretations for this integration. Original Mother Nature and Purple Goddess artwork: created with OpenAI's built-in image generator and reviewed for this project. Fallback scans: [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json). Placeholder back: [Wikimedia — red card back](https://commons.wikimedia.org/wiki/File:Card_back_red.svg). Entertainment only, not professional advice.

**License:** [MIT](LICENSE). Issues/PRs: this repo’s `issue_tracker` in `manifest.json`.
