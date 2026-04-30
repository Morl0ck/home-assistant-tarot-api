# Tarot API — Home Assistant

Custom integration: pull a random Rider–Waite–Smith card over HTTP, expose a native **`image`** entity for Picture cards, plus a **`sensor`** (meanings, upright/reversed) and a **`button`** to draw again.

**Data sources**

- **Default:** [tarotapi.dev](https://tarotapi.dev) ([ekelen/tarot-api](https://github.com/ekelen/tarot-api)). Card art is resolved from [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json) on GitHub (`name_short` → scan URLs). No image server required.
- **Optional:** [krates98/tarotcardapi](https://github.com/krates98/tarotcardapi) on your network; set its base URL in the flow (not `tarotapi.dev`).

**Requirements:** Home Assistant **2023.8+**. Outbound HTTPS to the API you use and, for default art, `raw.githubusercontent.com`.

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
| tarotapi.dev | Waite text from the public API; optional override of API base URL if you self-host the same API. |
| krates98 | Your server, e.g. `http://192.168.1.10:3000`. |

---

## Entities

One device (e.g. “Tarot draw”): **Draw** button, **Tarot card** sensor, **Tarot card face** image. Check **Developer tools → States** for exact `entity_id`s.

Picture Entity card **`entity`** must be **`image.…`**, not the sensor — HA only treats camera/image/person as image sources there. Example layout: [`examples/tarot_dashboard_card.yaml`](examples/tarot_dashboard_card.yaml).

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
| No artwork | HA can reach GitHub raw URLs and your API host. |

**Publishing your own fork:** [`scripts/publish-github.ps1`](scripts/publish-github.ps1) — `gh auth login`, then run from repo root (adjust `$RepoName` if needed). Or `gh repo create … --source=. --push` and align `manifest.json` URLs.

---

## Credits

API / text: [ekelen/tarot-api](https://github.com/ekelen/tarot-api). Default scans: [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json). Placeholder back: [Wikimedia — red card back](https://commons.wikimedia.org/wiki/File:Card_back_red.svg). Entertainment only, not professional advice.

**License:** [MIT](LICENSE). Issues/PRs: this repo’s `issue_tracker` in `manifest.json`.
