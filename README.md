# Tarot API — Home Assistant

Custom integration: pull a random Rider–Waite–Smith card over HTTP, expose a native **`image`** entity for Picture cards, plus a **`sensor`** with original bundled upright/reversed readings and a **`button`** to draw again.

**Data sources**

- **Default:** [tarotapi.dev](https://tarotapi.dev) ([ekelen/tarot-api](https://github.com/ekelen/tarot-api)). Card art is resolved from [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json) on GitHub (`name_short` → scan URLs). No image server required.
- **Optional:** [krates98/tarotcardapi](https://github.com/krates98/tarotcardapi) on your network; set its base URL in the flow (not `tarotapi.dev`).
- **Readings:** all 156 interpretations are bundled in [`readings.json`](custom_components/tarot_api/readings.json). They load once in a background worker; reading text needs no AI service or additional API request. Providers still supply the random card.
- **Artwork:** two original 78-card decks are bundled locally: Mother Nature by day and Purple Goddess at night. Recognized cards use the original PNGs through Home Assistant's image proxy; external scans are a fallback.

**Requirements:** Home Assistant **2023.8+**. Outbound HTTPS to the API you use and, for default art, `raw.githubusercontent.com`.

## Daytime and nighttime artwork

Version **1.3.0** switches automatically with `sun.sun`: above the horizon selects **Mother Nature** and below the horizon selects **Purple Goddess**. A sunrise or sunset changes the artwork of the current card without drawing again or changing its orientation or reading. If Sun is absent or unavailable, the configured home location supplies the solar calculation, checked once a minute; if no solar event can be calculated, the nighttime theme is used.

Both decks contain all 78 canonical card IDs. The Purple Goddess title **The Goddess** maps to The Empress (`ar03`); **The Hanged One** maps to The Hanged Man (`ar12`). Readings retain their traditional card names. Both API providers use the same matching rules as the bundled readings.

The existing `image.*` entity and dashboard remain usable. The sensor picture mirrors the image proxy and adds `artwork_theme` and `artwork_url`; its existing `image_url` retains the provider's URL for compatibility. Local images are read in an executor and cached for the current card/theme. Missing or invalid PNGs and unknown cards fall back to provider artwork, with a warning for missing bundled assets.

For a manual update, copy the **entire** `custom_components/tarot_api` folder, including `artwork/mother_nature`, `artwork/purple_goddess`, and `artwork/index.json`, into Home Assistant's `config/custom_components`, then restart Home Assistant and draw a card. There are 156 original 1024 × 1536 PNGs; allow about 543 MiB for the artwork. Local checkout changes take effect in Home Assistant after copying them or installing a published update.

---

## Install

**HACS:** Integrations → menu → **Custom repositories** → URL `https://github.com/Morl0ck/home-assistant-tarot-api`, category **Integration**. Install, restart Home Assistant, then **Settings → Devices & services → Add integration → Tarot API**.

**Manual:** Copy [`custom_components/tarot_api`](custom_components/tarot_api) to `config/custom_components/tarot_api`, restart, add the integration.

If HACS errors with **`unexpected character: line 1 column 1`**, it’s usually wrong repo URL (repository root only, not `/tree/main` or raw), JSON saved with a **UTF-8 BOM**, bad HACS storage (`config/.storage/hacs.repositories` — backup, delete while HA stopped, restart), or wrong category (**Integration**). This repo keeps JSON UTF-8 without BOM and LF per [`.gitattributes`](.gitattributes).

---

## Configuration

One config entry is enough.

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

To apply a local update, copy the complete `custom_components/tarot_api` folder (including `readings.py` and `readings.json`) to Home Assistant, restart, and draw a new card. HACS installations do not see local checkout edits until those files are published or copied to Home Assistant.

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
| Local reading unavailable | Check logs and ensure `readings.json` was copied with the integration. After repairing the file, restart HA to reload the shared catalog. |

**Publishing your own fork:** [`scripts/publish-github.ps1`](scripts/publish-github.ps1) — `gh auth login`, then run from repo root (adjust `$RepoName` if needed). Or `gh repo create … --source=. --push` and align `manifest.json` URLs.

---

## Credits

Card metadata / original API text: [ekelen/tarot-api](https://github.com/ekelen/tarot-api). Bundled readings: original traditional, warm, reflective interpretations for this integration. Original Mother Nature and Purple Goddess artwork: created with OpenAI's built-in image generator and reviewed for this project. Fallback scans: [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json). Placeholder back: [Wikimedia — red card back](https://commons.wikimedia.org/wiki/File:Card_back_red.svg). Entertainment only, not professional advice.

**License:** [MIT](LICENSE). Issues/PRs: this repo’s `issue_tracker` in `manifest.json`.
