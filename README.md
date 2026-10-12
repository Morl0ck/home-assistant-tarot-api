# Tarot API — Home Assistant

Custom integration: draw a random Rider–Waite–Smith card over HTTP, display **Mother Nature artwork by day and Purple Goddess artwork at night**, and read an original bundled upright/reversed interpretation. Includes a native **`image`** entity for Picture cards, a **`sensor`** for the reading, and a **`button`** to draw again.

**Data sources**

- **Default:** [tarotapi.dev](https://tarotapi.dev) ([ekelen/tarot-api](https://github.com/ekelen/tarot-api)) supplies random card metadata. Recognized cards use the bundled artwork; [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json) scan URLs are retained as a fallback. No image server required.
- **Optional:** [krates98/tarotcardapi](https://github.com/krates98/tarotcardapi) on your network; set its base URL in the flow (not `tarotapi.dev`).
- **Readings:** all 156 interpretations are bundled in [`readings.json`](custom_components/tarot_api/readings.json). They load once in a background worker; reading text needs no AI service or additional API request. Providers still supply the random card.
- **Artwork:** two original 78-card decks are bundled locally: Mother Nature by day and Purple Goddess at night. Recognized cards use the original PNGs through Home Assistant's image proxy; external scans are a fallback.

**Requirements:** Home Assistant **2023.8+**, access to your chosen card API, and about **543 MiB** of storage for the artwork. Normal card images and readings load locally. External fallback images need access to their image host; the initial card-back placeholder needs access to Wikimedia.

## Daily Practice dashboard (1.4.1)

The new **Practice** card brings **Affirmations, Tarot, Oracle, Gods, and Runes** into one mobile dashboard. It uses a dark lavender palette, warm accent buttons, a locally drawn moon landscape, and horizontally scrolling tabs. It is an original interface inspired by a daily practice screen; its content and artwork are not copied from Moonly. No frontend libraries, card-mod, subscription, or AI account are required.

The four new collections are bundled in `practices.json`: **32 affirmations**, **18 original Oracle cards**, **12 mixed Greek/Norse/Egyptian deity cards**, and **24 Elder Futhark runes**. Each contains an original modern interpretation, a reflection question, and a small practice. Deity cards also include a short mythology profile, with a reference URL in their sensor attributes. These profiles were checked against the Bank of Greece's mythology collection, the Metropolitan Museum of Art, and World History Encyclopedia. Deity and rune readings are modern reflective writing rather than ancient prayers or translations. Tarot continues to use the existing provider, 78-card decks, and upright/reversed readings.

Affirmations, Oracle, Gods, and Runes receive a daily selection automatically. They rotate through every item before repeating, remain the same across devices, and refresh within one minute of midnight in **Home Assistant's configured timezone**. Draw buttons select a different item in that collection. Manual choices survive restarts on the same local day, stored per integration entry in HA's `.storage`; the next day resets them. These four collections need no network requests. Tarot retains its existing manual draw and API behavior, including starting without a card after a restart.

### Open Daily Practice

1. Install or update **Tarot API** through HACS and restart Home Assistant. For a manual installation, copy the complete `custom_components/tarot_api` directory, including its `frontend`, catalogs and artwork directories. New installations also need **Settings → Devices & services → Add integration → Tarot API**; existing installations keep their integration entry.
2. Refresh your browser or Companion app and open **Daily Practice** in the Home Assistant sidebar.

The integration serves its bundled JavaScript, registers the sidebar page, and connects the five tabs to the entity IDs in Home Assistant's registry automatically. No `www` copy, dashboard resource, or YAML setup is needed for this page. Renaming an entity updates its mapping; multiple integration entries each get an independent page. The page is available to regular Home Assistant users, including your wife. Unloading or removing the integration removes its page.

### Optional: add the card to an existing dashboard

For a card inside your own Lovelace dashboard, add **`/tarot_api_static/moon-practice-card.js?v=1.4.1`** as a **JavaScript module** dashboard resource and refresh the browser or Companion app. Paste the `custom:moon-practice-card` block from [`examples/moon_practice_dashboard.yaml`](examples/moon_practice_dashboard.yaml) into a Manual card, or use the full example in a dashboard's **Raw configuration editor**. This follows [Home Assistant's custom card installation](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/#referencing-your-new-card). Check **Developer tools → States** and adjust its sensor and button IDs, especially with multiple integration entries or name collisions. The bundled file replaces the manual `www` copy used in 1.4.0.

| Tab | Default sensor | Default button |
|-----|----------------|----------------|
| Affirmations | `sensor.daily_affirmation` | `button.new_affirmation` |
| Tarot | `sensor.tarot_card` | `button.draw_tarot_card` |
| Oracle | `sensor.oracle_card` | `button.draw_oracle_card` |
| Gods | `sensor.deity_card` | `button.draw_deity_card` |
| Runes | `sensor.rune` | `button.draw_rune` |

The default tab is `affirmation`. Set `default_tab` to `tarot`, `oracle`, `deity`, or `rune` to choose another. Names and text wrap rather than truncate; swipe the tab row to reach later sections. Keyboard users can navigate tabs with Left/Right, Home, and End. Missing entities and failed draws show a message inside the card. Tarot uses the image proxy, updates with the existing day/night decks, and rotates reversed cards automatically.

For a local, interactive preview using sample HA states, run `python -m http.server 8766 --bind 127.0.0.1` from the repository root and open `http://127.0.0.1:8766/examples/moon_practice_preview.html`. Append `?panel=1` to exercise the sidebar wrapper with renamed sample entities. The preview exercises the real UI with bundled text and artwork; it is not connected to your live Home Assistant. Install the integration there using the steps above. To customize the writing, edit [`scripts/build-practice-catalog.py`](scripts/build-practice-catalog.py), run it once, then copy the regenerated `practices.json` into HA and restart.

## Daytime and nighttime artwork

Version **1.3.0** switches automatically with `sun.sun`: above the horizon selects **Mother Nature** and below the horizon selects **Purple Goddess**. A sunrise or sunset changes the artwork of the current card without drawing again or changing its orientation or reading. If Sun is absent or unavailable, the configured home location supplies the solar calculation, checked once a minute; if no solar event can be calculated, the nighttime theme is used.

Both decks contain all 78 canonical card IDs. The Purple Goddess title **The Goddess** maps to The Empress (`ar03`); **The Hanged One** maps to The Hanged Man (`ar12`). Readings retain their traditional card names. Both API providers use the same matching rules as the bundled readings.

The existing `image.*` entity and dashboard remain usable. The sensor picture mirrors the image proxy and adds `artwork_theme` and `artwork_url`; its existing `image_url` retains the provider's URL for compatibility. Local images are read in an executor and cached for the current card/theme. Missing or invalid PNGs and unknown cards fall back to provider artwork, with a warning for missing bundled assets.

For a manual update, copy the **entire** `custom_components/tarot_api` folder, including `artwork/mother_nature`, `artwork/purple_goddess`, and `artwork/index.json`, into Home Assistant's `config/custom_components`, then restart Home Assistant and draw a card. There are 156 original 1024 × 1536 PNGs; allow about 543 MiB for the artwork. Local checkout changes take effect in Home Assistant after copying them or installing a published update.

---

## Install

**HACS:** Integrations → menu → **Custom repositories** → URL `https://github.com/Morl0ck/home-assistant-tarot-api`, category **Integration**. Install, restart Home Assistant, then **Settings → Devices & services → Add integration → Tarot API**.

**Manual:** Copy the complete [`custom_components/tarot_api`](custom_components/tarot_api) directory to `config/custom_components/tarot_api`, including `readings.json` and both `artwork` subdirectories. Restart Home Assistant, then add the integration.

**Updating an existing installation:** Install the repository update through HACS, or replace the complete integration directory manually. Restart Home Assistant, refresh the browser or Companion app, and open **Daily Practice** in the sidebar. Draw a Tarot card to populate that tab. Existing entity IDs and dashboards remain compatible; automatic artwork switching needs no extra automation. Confirm the integration's `manifest.json` reports version **1.4.1** and set your home location correctly under Home Assistant's system settings. HACS installs the bundled Practice UI along with the integration.

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
