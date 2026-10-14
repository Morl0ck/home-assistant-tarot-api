/* Original bundled Home Assistant Practice card. No framework or CDN. */
const PRACTICE_TABS = [
  { key: "affirmation", label: "Affirmations", entity: "sensor.daily_affirmation", button: "button.new_affirmation", action: "Another affirmation" },
  { key: "tarot", label: "Tarot", entity: "sensor.tarot_card", button: "button.draw_tarot_card", action: "Draw a card" },
  { key: "oracle", label: "Oracle", entity: "sensor.oracle_card", button: "button.draw_oracle_card", action: "Draw a card" },
  { key: "deity", label: "Gods", entity: "sensor.deity_card", button: "button.draw_deity_card", action: "Draw a deity" },
  { key: "rune", label: "Runes", entity: "sensor.rune", button: "button.draw_rune", action: "Draw a rune" },
  { key: "horoscope", label: "Horoscopes", entity: "sensor.daily_horoscope", button: "button.refresh_horoscopes", action: "Refresh horoscopes" },
];
const ZODIAC_SIGNS = ["aries","taurus","gemini","cancer","leo","virgo","libra","scorpio","sagittarius","capricorn","aquarius","pisces"];
const ZODIAC_SYMBOLS = ["♈︎","♉︎","♊︎","♋︎","♌︎","♍︎","♎︎","♏︎","♐︎","♑︎","♒︎","♓︎"];
const signName = (sign) => sign.charAt(0).toUpperCase() + sign.slice(1);
const escapeText = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const available = (entity) => entity && !["unknown", "unavailable"].includes(entity.state);
// A button that has never been pressed has state "unknown" but is usable.
const buttonAvailable = (entity) => entity && entity.state !== "unavailable";
function imageUrl(value) {
  if (typeof value !== "string" || !value.trim()) return "";
  try {
    const url = new URL(value, window.location.href);
    return ["http:", "https:"].includes(url.protocol) ? escapeText(url.href) : "";
  } catch { return ""; }
}

const STYLES = `
  :host { display:block; width:100%; max-width:1280px; margin-inline:auto; container-type:inline-size; color:#f7f1eb; font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif); }
  * { box-sizing:border-box; }
  ha-card { display:block; padding:28px 22px 22px; background:#19181f; border:1px solid #35313f; border-radius:30px; overflow:hidden; color:#f7f1eb; }
  header { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:24px; }
  .eyebrow { margin:0 0 6px; color:#bcb1c4; font-size:10px; letter-spacing:.22em; text-transform:uppercase; }
  h1 { margin:0; font:500 46px/1.1 Georgia,'Times New Roman',serif; letter-spacing:-.035em; }
  .header-moon { font:52px Georgia,serif; color:#d9bd95; padding-right:5px; }
  .tabs { display:flex; gap:8px; overflow-x:auto; scrollbar-width:thin; scrollbar-color:#65546f transparent; padding:2px 2px 13px; margin-bottom:9px; }
  button { font:inherit; cursor:pointer; -webkit-tap-highlight-color:transparent; }
  .tab { flex:0 0 auto; border:1px solid transparent; border-radius:28px; padding:12px 18px; background:#27252e; color:#e0d8e6; font-size:13px; font-weight:600; }
  .tab[aria-selected=true] { background:#e9ad70; color:#281c1c; }
  button:focus-visible { outline:3px solid #ffe1b2; outline-offset:3px; }
  .panel { border-radius:24px; overflow:hidden; background:#30293b; }
  .hero { position:relative; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; min-height:410px; padding:42px 25px 160px; text-align:center; overflow:hidden; isolation:isolate; background:radial-gradient(ellipse at 50% 82%,#ad829255 0,transparent 54%),linear-gradient(165deg,#51465d,#766177 60%,#9c7d8a); }
  .hero.day { background:radial-gradient(ellipse at 50% 82%,#f1cc9a55 0,transparent 54%),linear-gradient(160deg,#536067,#837878 58%,#bea083); }
  .overline { margin:0 0 22px; color:#f3eaf1b8; text-transform:uppercase; font-size:10px; font-weight:600; letter-spacing:.19em; z-index:2; }
  .hero h2 { margin:0; font:500 clamp(27px,7vw,40px)/1.23 Georgia,'Times New Roman',serif; text-wrap:balance; overflow-wrap:anywhere; max-width:430px; z-index:2; }
  .tradition { z-index:2; font-size:12px; letter-spacing:.08em; color:#e3d4e5; margin:12px 0 0; }
  .landscape { position:absolute; bottom:0; left:0; width:100%; height:190px; z-index:-1; }
  .orb { position:absolute; width:87px; height:87px; border-radius:50%; bottom:71px; left:calc(50% - 43.5px); background:radial-gradient(circle at 35% 30%,#f9e7b3,#d8bb78); box-shadow:0 0 45px #efc98c48; z-index:-1; }
  .stars { position:absolute; inset:0; pointer-events:none; z-index:-1; background-image:radial-gradient(circle at 14% 24%,#fff7db70 0 1px,transparent 1.5px),radial-gradient(circle at 79% 36%,#fff7db70 0 1px,transparent 1.5px),radial-gradient(circle at 86% 15%,#fff7db70 0 1px,transparent 1.5px),radial-gradient(circle at 30% 63%,#fff7db70 0 1px,transparent 1.5px); }
  .symbol { font:100px/1.2 Georgia,'Segoe UI Symbol','Noto Sans Runic',serif; margin:25px 0 0; color:#f3d5a3; text-shadow:0 0 40px #efc98c30; z-index:2; }
  .hero.symbolic { min-height:330px; padding-bottom:46px; }
  .hero.tarot { padding:30px 20px; min-height:310px; }
  .tarot .overline { margin-bottom:12px; }
  .tarot h2 { font-size:28px; margin-bottom:18px; }
  .art { max-width:235px; width:75%; height:auto; border-radius:13px; display:block; box-shadow:0 14px 35px #17121b65; }
  .art.reversed { transform:rotate(180deg); }
  .reading { padding:25px; }
  .keywords { display:flex; flex-wrap:wrap; justify-content:center; gap:7px; margin:0 0 22px; }
  .keyword { font-size:10px; letter-spacing:.03em; color:#e4cedd; background:#ffffff0a; border:1px solid #ffffff12; padding:6px 10px; border-radius:16px; }
  p { line-height:1.7; font-size:14px; color:#ded4e0; margin:0; white-space:pre-line; overflow-wrap:anywhere; }
  .block { margin-top:24px; }
  .block h3 { margin:0 0 7px; color:#eac797; font-size:10px; text-transform:uppercase; letter-spacing:.16em; font-weight:600; }
  .reflection { font:italic 18px/1.5 Georgia,'Times New Roman',serif; color:#f5e8f0; }
  .draw { display:block; width:100%; background:#e9ad70; color:#281c1c; border:0; border-radius:16px; margin-top:26px; padding:15px; font-size:13px; font-weight:700; }
  .draw:disabled { opacity:.5; cursor:default; }
  .status { font-size:12px; margin-top:14px; color:#f4ceba; }
  .empty { padding:35px 24px; }
  .empty h2 { font:26px Georgia,serif; margin:0 0 14px; }
  footer { text-align:center; margin:19px 0 0; color:#a89aae; font-size:10px; letter-spacing:.07em; }
  ha-card.single { background:transparent; border:0; border-radius:0; padding:24px 12px; }
  .single .tabs, .single .eyebrow, .single footer { display:none; }
  .single h1 { font-size:30px; letter-spacing:0; }
  .single header { margin-bottom:20px; }
  .single .header-moon { font-size:30px; }
  .sign-picker { padding:24px; background:#19181f; }
  .sign-picker h2 { font-size:11px; font-weight:500; text-transform:uppercase; letter-spacing:.16em; color:#eac797; margin:0 0 18px; }
  .sign-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
  .sign { display:flex; flex-direction:column; align-items:center; gap:5px; border:1px solid #494052; background:#27252e; color:#f7f1eb; border-radius:12px; padding:13px 4px; min-height:64px; font-size:12px; }
  .sign span { font:28px Georgia,'Segoe UI Symbol',serif; color:#f3d5a3; }
  .sign[aria-pressed=true] { border-color:#e9ad70; background:#4a3b3e; }
  .sign-select { display:none; width:100%; font:16px system-ui,sans-serif; padding:12px; background:#27252e; color:#f7f1eb; border:1px solid #65546f; border-radius:9px; }
  .horoscope-heading { font:30px Georgia,serif; color:#f7f1eb; margin:0 0 22px; }
  .source { margin-top:24px; font-size:12px; color:#bcb1c4; }
  .source a { color:inherit; }
  .draw.quiet { width:auto; background:transparent; color:#e9ad70; padding:10px 0; text-align:left; }
  @container (min-width:700px) {
    .panel { display:grid; grid-template-columns:minmax(0,.95fr) minmax(0,1.05fr); gap:24px; background:transparent; border-radius:0; align-items:start; }
    .hero, .reading, .sign-picker { border-radius:24px; }
    .hero { min-height:450px; padding-top:50px; }
    .hero.symbolic { min-height:430px; justify-content:center; }
    .hero.tarot { min-height:430px; }
    .art { max-width:290px; }
    .reading { background:#30293b; padding:30px; }
    .empty { grid-column:1/-1; background:#30293b; border-radius:24px; }
  }
  @container (max-width:699px) { .sign-grid { display:none; } .sign-select { display:block; } }
  .tarot-controls { display:flex; flex-wrap:wrap; gap:8px; margin:0 0 22px; }
  .tarot-controls[hidden] { display:none; }
  .tarot-mode { background:#27252e; color:#e0d8e6; border:1px solid #494052; border-radius:20px; padding:10px 18px; min-height:44px; font-size:13px; }
  .tarot-mode[aria-pressed=true] { background:#e9ad70; color:#281c1c; border-color:#e9ad70; }
  .panel.spread { display:grid; grid-template-columns:1fr; gap:22px; background:transparent; border-radius:0; }
  .spread-card { min-width:0; border-radius:24px; overflow:hidden; background:#30293b; }
  .spread-card .hero.tarot { min-height:0; padding:24px 18px; border-radius:0; }
  .spread-card .hero h2 { font-size:24px; }
  .spread-card .reading { padding:24px; border-radius:0; }
  .spread-card .art { max-width:230px; width:80%; }
  .spread-card .position { color:#f3d5a3; margin-bottom:10px; font-size:12px; }
  .spread-actions { grid-column:1/-1; }
  .spread-actions .draw { margin-top:0; }
  @container (min-width:800px) { .panel.spread { grid-template-columns:repeat(3,minmax(0,1fr)); align-items:start; } }
  @media(max-width:360px) { ha-card { padding:22px 14px 17px; } .reading { padding:22px 19px; } h1 { font-size:40px; } .tab { padding:12px 15px; } }
`;

class MoonPracticeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._active = "affirmation";
    this._errors = {};
    this._sign = "aries";
    this._tarotCount = 1;
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><ha-card>
      <header><div><p class="eyebrow">A little space for yourself</p><h1>Practice</h1></div><span class="header-moon" aria-hidden="true">☾</span></header>
      <nav class="tabs" role="tablist" aria-label="Practice sections"></nav>
      <div class="tarot-controls" role="group" aria-label="Tarot draw size" hidden><button class="tarot-mode" data-card-count="1">One card</button><button class="tarot-mode" data-card-count="3">Three cards</button></div>
      <section class="panel" id="practice-panel" role="tabpanel" aria-live="polite"></section>
      <footer>A moment to pause, a little room to grow.</footer></ha-card>`;
    const tabs = this.shadowRoot.querySelector(".tabs");
    tabs.innerHTML = PRACTICE_TABS.map((tab) => `<button class="tab" role="tab" id="tab-${tab.key}" data-tab="${tab.key}" aria-controls="practice-panel">${tab.label}</button>`).join("");
    this.shadowRoot.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-tab]");
      if (tab) this._select(tab.dataset.tab);
      if (event.target.closest("[data-draw]")) this._draw();
      const sign = event.target.closest("[data-sign]");
      if (sign) this._chooseSign(sign.dataset.sign);
      const mode = event.target.closest("[data-card-count]");
      if (mode && !this._busy) { this._tarotCount=Number(mode.dataset.cardCount); this._render(); }
    });
    this.shadowRoot.addEventListener("change", (event) => {
      if (event.target.matches("[data-sign-select]")) this._chooseSign(event.target.value);
    });
    tabs.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const current = PRACTICE_TABS.findIndex((tab) => tab.key === this._active);
      const count = PRACTICE_TABS.length;
      const index = event.key === "Home" ? 0 : event.key === "End" ? count - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + count) % count;
      this._select(PRACTICE_TABS[index].key, true);
    });
  }

  setConfig(config) {
    for (const key of [config.default_tab, config.section]) {
      if (key && !PRACTICE_TABS.some((tab) => tab.key === key)) throw new Error("Unknown practice section. Use affirmation, tarot, oracle, deity, rune, or horoscope.");
    }
    if (config.sign && !ZODIAC_SIGNS.includes(config.sign)) throw new Error("Unknown zodiac sign. Use a lowercase sign name such as aries.");
    if (config.spread_labels && (!Array.isArray(config.spread_labels) || config.spread_labels.length !== 3 || config.spread_labels.some(label => typeof label !== "string" || !label.trim()))) throw new Error("spread_labels must contain three nonempty labels.");
    const mappings = {};
    for (const tab of PRACTICE_TABS) {
      const mapping = config[tab.key] ?? {};
      const entity = mapping.entity ?? tab.entity;
      const button = mapping.button ?? tab.button;
      if (typeof entity !== "string" || !/^sensor\.[a-z0-9_]+$/.test(entity)) throw new Error(`${tab.label}: entity must be a sensor entity ID.`);
      if (typeof button !== "string" || !/^button\.[a-z0-9_]+$/.test(button)) throw new Error(`${tab.label}: button must be a button entity ID.`);
      mappings[tab.key] = { entity, button };
    }
    const spreadEntity = config.tarot?.spread_entity ?? "sensor.tarot_spread";
    const spreadButton = config.tarot?.spread_button ?? "button.draw_three_tarot_cards";
    if (typeof spreadEntity !== "string" || !/^sensor\.[a-z0-9_]+$/.test(spreadEntity)) throw new Error("Tarot: spread_entity must be a sensor entity ID.");
    if (typeof spreadButton !== "string" || !/^button\.[a-z0-9_]+$/.test(spreadButton)) throw new Error("Tarot: spread_button must be a button entity ID.");
    Object.assign(mappings.tarot, {spread_entity:spreadEntity, spread_button:spreadButton});
    this._config = { ...config, ...mappings };
    this._registryResolved = false;
    this._active = config.section || config.default_tab || "affirmation";
    this.shadowRoot.querySelector("ha-card").classList.toggle("single", Boolean(config.section));
    this.shadowRoot.querySelector("h1").textContent = config.section ? PRACTICE_TABS.find(tab => tab.key === config.section).label : "Practice";
    this._sign = config.sign || "aries";
    this._signKey = `tarot-api-zodiac:${config.entry_id || mappings.horoscope.entity}`;
    try { const saved = localStorage.getItem(this._signKey); if (ZODIAC_SIGNS.includes(saved)) this._sign = saved; } catch { /* Private browsers may disable storage. */ }
    this._resolveRegistry();
    this._render();
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    this._resolveRegistry();
    if (!this._config) return;
    const mapping = this._config[this._active];
    const relevant = [mapping.entity, mapping.button, "sun.sun"];
    if (this._active === "tarot") relevant.push(mapping.spread_entity, mapping.spread_button);
    if (!previous || relevant.some((id) => previous.states[id] !== hass.states[id])) this._render();
  }

  getCardSize() { return 12; }
  getGridOptions() { return { columns: "full", rows: "auto" }; }
  static getStubConfig() { return { type: "custom:moon-practice-card" }; }

  _select(key, focus = false) {
    this._active = key;
    this._render();
    const tab = this.shadowRoot.querySelector(`[data-tab="${key}"]`);
    if (focus) tab.focus();
    tab.scrollIntoView({ behavior: "auto", block: "nearest", inline: "nearest" });
  }

  _render() {
    if (!this._config) return;
    const tab = PRACTICE_TABS.find((item) => item.key === this._active);
    const mapping = this._config[this._active];
    const state = this._hass?.states[mapping.entity];
    const attrs = state?.attributes || {};
    const drawButton = this._hass?.states[mapping.button];
    const panel = this.shadowRoot.querySelector(".panel");
    const drawFocused = this.shadowRoot.activeElement?.hasAttribute("data-draw");
    const spread = this._active === "tarot" && this._tarotCount === 3;
    panel.classList.toggle("spread", spread);
    this.shadowRoot.querySelector(".tarot-controls").hidden = this._active !== "tarot";
    for (const mode of this.shadowRoot.querySelectorAll("[data-card-count]")) {
      mode.setAttribute("aria-pressed", String(Number(mode.dataset.cardCount) === this._tarotCount));
      mode.disabled=Boolean(this._busy);
    }
    for (const button of this.shadowRoot.querySelectorAll("[data-tab]")) {
      const selected = button.dataset.tab === this._active;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    }
    panel.setAttribute("aria-labelledby", `tab-${this._active}`);
    const waiting = this._busy === this._active;
    const canDraw = buttonAvailable(drawButton) && !this._busy;
    if (spread) {
      this._renderSpread(panel, mapping);
      if (drawFocused) panel.querySelector("[data-draw]").focus({preventScroll:true});
      return;
    }
    if (this._active === "horoscope") {
      this._renderHoroscope(panel, attrs, state, drawButton, canDraw, waiting);
      if (drawFocused) panel.querySelector("[data-draw]").focus({preventScroll:true});
      return;
    }
    let content;
    if (!available(state)) {
      const message = !state ? `Add or check the entity ${mapping.entity} in this card's configuration.` : state.state === "unknown" && this._active === "tarot" ? "Draw your first card and take a moment to see what it brings to mind." : "This practice is unavailable. Check the integration and try again.";
      content = `<div class="empty"><p class="overline">${escapeText(tab.label)}</p><h2>A moment awaits</h2><p>${escapeText(message)}</p>`;
    } else {
      const name = attrs.card_name || attrs.name || state.state;
      const day = this._hass?.states["sun.sun"]?.state === "above_horizon";
      const date = attrs.date || "";
      const overline = this._active === "tarot" ? (attrs.orientation === "reversed" ? "Reversed" : "Upright") : "Today";
      const isTarot = this._active === "tarot";
      const isAffirmation = this._active === "affirmation";
      const art = imageUrl(attrs.artwork_url || attrs.entity_picture);
      const scene = `<div class="stars"></div><div class="orb"></div><svg class="landscape" viewBox="0 0 600 220" preserveAspectRatio="none" aria-hidden="true"><path d="M0 170 Q90 10 190 150 T400 150 T600 120 V220 H0Z" fill="#615169"/><path d="M0 140 Q90 220 230 155 T420 160 T600 100 V220 H0Z" fill="#43384f"/><path d="M0 190 Q140 130 280 195 T600 170 V220 H0Z" fill="#302939"/></svg>`;
      content = `<div class="hero ${day ? "day" : ""} ${isTarot ? "tarot" : isAffirmation ? "" : "symbolic"}">
        <p class="overline">${escapeText(overline)}${date ? ` · ${escapeText(date)}` : ""}</p>
        <h2>${escapeText(name)}</h2>
        ${attrs.tradition ? `<p class="tradition">${escapeText(attrs.tradition)} tradition · Modern reflection</p>` : ""}
        ${isTarot && art ? `<img class="art ${attrs.orientation === "reversed" ? "reversed" : ""}" src="${art}" alt="${escapeText(name)}" loading="lazy">` : ""}
        ${!isTarot && !isAffirmation ? `<div class="symbol" aria-hidden="true">${escapeText(attrs.symbol || "✦")}</div>` : ""}
        ${isAffirmation ? scene : `<div class="stars"></div>`}
        </div><div class="reading">
        ${Array.isArray(attrs.keywords) && !isAffirmation ? `<div class="keywords">${attrs.keywords.map((word) => `<span class="keyword">${escapeText(word)}</span>`).join("")}</div>` : ""}
        ${attrs.lore ? `<div class="block" style="margin:0 0 24px"><h3>From the tradition</h3><p>${escapeText(attrs.lore)}</p></div>` : ""}
        <p>${escapeText(attrs.interpretation || "A local reading is not available for this card.")}</p>
        ${attrs.reflection ? `<div class="block"><h3>A question for you</h3><p class="reflection">${escapeText(attrs.reflection)}</p></div>` : ""}
        ${attrs.practice ? `<div class="block"><h3>A small practice</h3><p>${escapeText(attrs.practice)}</p></div>` : ""}`;
    }
    content += `<button class="draw" data-draw ${canDraw ? "" : "disabled"}>${waiting ? "Drawing…" : escapeText(tab.action)}</button>
      ${!buttonAvailable(drawButton) ? `<p class="status">Draw button unavailable: ${escapeText(mapping.button)}</p>` : ""}
      ${this._errors[this._active] ? `<p class="status" role="alert">${escapeText(this._errors[this._active])}</p>` : ""}</div>`;
    panel.innerHTML = content;
    if (drawFocused) panel.querySelector("[data-draw]").focus({ preventScroll: true });
  }

  async _draw() {
    if (this._busy || !this._hass || !this._config) return;
    const kind = this._active;
    const restoreFocus = this.shadowRoot.activeElement?.hasAttribute("data-draw") ? "[data-draw]" : null;
    const entityId = kind === "tarot" && this._tarotCount === 3 ? this._config.tarot.spread_button : this._config[kind].button;
    if (!buttonAvailable(this._hass.states[entityId])) return;
    this._busy = kind;
    delete this._errors[kind];
    this._render();
    try {
      await this._hass.callService("button", "press", { entity_id: entityId });
    } catch (error) {
      this._errors[kind] = `${kind === "horoscope" ? "Could not refresh." : "Could not draw."} ${error?.message || "Please try again."}`;
    } finally {
      this._busy = null;
      this._render();
      if (restoreFocus && this._active === kind) this.shadowRoot.querySelector(restoreFocus)?.focus({ preventScroll: true });
    }
  }

  _renderSpread(panel, mapping) {
    const state = this._hass?.states[mapping.spread_entity];
    const button = this._hass?.states[mapping.spread_button];
    const cards = state?.attributes?.cards;
    const labels = this._config.spread_labels || ["Past", "Present", "Future"];
    const waiting = this._busy === "tarot";
    const canDraw = buttonAvailable(button) && !this._busy;
    if (available(state) && Array.isArray(cards) && cards.length === 3) {
      panel.innerHTML = cards.map((card,index) => {
        const name=card.card_name || "Unknown card";
        const art=imageUrl(card.artwork_url || card.entity_picture);
        const reversed=card.orientation === "reversed";
        const day=card.artwork_theme === "mother_nature";
        return `<article class="spread-card" aria-label="${escapeText(labels[index])}: ${escapeText(name)}">
          <div class="hero tarot ${day ? "day" : ""}"><p class="position">${escapeText(labels[index])}</p><p class="overline">${reversed ? "Reversed" : "Upright"}</p><h2>${escapeText(name)}</h2>
          ${art ? `<img class="art ${reversed ? "reversed" : ""}" src="${art}" alt="${escapeText(name)}" loading="lazy">` : `<p class="status">Artwork unavailable</p>`}</div>
          <div class="reading">${Array.isArray(card.keywords) ? `<div class="keywords">${card.keywords.map(word => `<span class="keyword">${escapeText(word)}</span>`).join("")}</div>` : ""}
          <p>${escapeText(card.interpretation || "A local reading is not available for this card.")}</p>
          ${card.reflection ? `<div class="block"><h3>A question for you</h3><p class="reflection">${escapeText(card.reflection)}</p></div>` : ""}</div></article>`;
      }).join("");
    } else {
      const message = !state ? `Check the spread sensor ${mapping.spread_entity} in this card's configuration.` : state.state === "unavailable" ? "The three-card spread is unavailable. Check the integration and try again." : `Draw three cards for ${labels.join(", ").toLowerCase()}. Each has its own orientation and reading.`;
      panel.innerHTML = `<div class="empty"><p class="overline">Three-card spread</p><h2>A little more perspective</h2><p>${escapeText(message)}</p></div>`;
    }
    panel.innerHTML += `<div class="spread-actions"><button class="draw" data-draw ${canDraw ? "" : "disabled"}>${waiting ? "Drawing…" : "Draw three cards"}</button>
      ${!buttonAvailable(button) ? `<p class="status">Three-card draw button unavailable: ${escapeText(mapping.spread_button)}</p>` : ""}
      ${this._errors.tarot ? `<p class="status" role="alert">${escapeText(this._errors.tarot)}</p>` : ""}</div>`;
  }

  _chooseSign(sign) {
    if (!ZODIAC_SIGNS.includes(sign)) return;
    const focused = this.shadowRoot.activeElement;
    const wasSelect = focused?.hasAttribute("data-sign-select");
    this._sign = sign;
    try { localStorage.setItem(this._signKey, sign); } catch { /* Optional persistence. */ }
    this._render();
    if (wasSelect) this.shadowRoot.querySelector("[data-sign-select]")?.focus({preventScroll:true});
    else this.shadowRoot.querySelector(`[data-sign="${sign}"]`)?.focus({preventScroll:true});
  }

  _renderHoroscope(panel, attrs, state, drawButton, canDraw, waiting) {
    const record = attrs.readings?.[this._sign];
    const error = attrs.errors?.[this._sign];
    const name = signName(this._sign);
    const symbol = ZODIAC_SYMBOLS[ZODIAC_SIGNS.indexOf(this._sign)];
    const message = !state ? "Check the horoscope sensor in this card's configuration." : error || "Your horoscope is loading. It will appear here when the daily feed is available.";
    panel.innerHTML = `<div class="sign-picker"><h2 id="zodiac-label">Your zodiac sign</h2>
      <select class="sign-select" data-sign-select aria-labelledby="zodiac-label">${ZODIAC_SIGNS.map(sign => `<option value="${sign}" ${sign === this._sign ? "selected" : ""}>${signName(sign)}</option>`).join("")}</select>
      <div class="sign-grid" role="group" aria-labelledby="zodiac-label">${ZODIAC_SIGNS.map((sign,i) => `<button class="sign" data-sign="${sign}" aria-pressed="${sign === this._sign}"><span aria-hidden="true">${ZODIAC_SYMBOLS[i]}</span>${signName(sign)}</button>`).join("")}</div></div>
      <div class="reading"><p class="overline">Daily horoscope${record?.date ? ` · ${escapeText(record.date)}` : ""}</p>
      <h2 class="horoscope-heading"><span aria-hidden="true">${symbol}</span> ${name}</h2>
      <p>${escapeText(record?.interpretation || message)}</p>
      ${record?.stale ? `<p class="status">Showing the last saved reading${error ? `. ${escapeText(error)}` : ". Today's reading is not available yet."}</p>` : record && error ? `<p class="status">${escapeText(error)}</p>` : ""}
      <button class="draw quiet" data-draw ${canDraw ? "" : "disabled"}>${waiting ? "Refreshing…" : "↻ Refresh horoscopes"}</button>
      ${!buttonAvailable(drawButton) ? `<p class="status">Refresh button unavailable: ${escapeText(this._config.horoscope.button)}</p>` : ""}
      ${this._errors.horoscope ? `<p class="status" role="alert">${escapeText(this._errors.horoscope)}</p>` : ""}
      <p class="source"><a href="https://freehoroscopeapi.com/" target="_blank" rel="noopener noreferrer">Free Horoscope API</a>${record ? " · Saved locally" : ""}</p></div>`;
  }

  async _resolveRegistry() {
    const config = this._config;
    if (!config?.entry_id || !this._hass?.callWS || this._registryPending || this._registryResolved) return;
    this._registryPending = true;
    try {
      const records = await this._hass.callWS({type:"config/entity_registry/list"});
      if (this._config !== config) return;
      for (const tab of PRACTICE_TABS) {
        const sensor = tab.key === "tarot" ? "card" : tab.key === "horoscope" ? "horoscope" : `practice_${tab.key}`;
        const button = tab.key === "tarot" ? "draw" : tab.key === "horoscope" ? "horoscope_refresh" : `practice_draw_${tab.key}`;
        for (const [domain, suffix, field] of [["sensor",sensor,"entity"],["button",button,"button"]]) {
          const record = records.find(r => r.config_entry_id === config.entry_id && r.platform === "tarot_api" && r.unique_id === `${config.unique_prefix}_${suffix}` && r.entity_id.startsWith(`${domain}.`));
          config[tab.key][field] = record?.entity_id || `${domain}.tarot_api_missing_${tab.key}`;
        }
      }
      for (const [domain,suffix,field] of [["sensor","spread","spread_entity"],["button","draw_three","spread_button"]]) {
        const record=records.find(r=>r.config_entry_id === config.entry_id && r.platform === "tarot_api" && r.unique_id === `${config.unique_prefix}_${suffix}` && r.entity_id.startsWith(`${domain}.`));
        config.tarot[field]=record?.entity_id || `${domain}.tarot_api_missing_spread`;
      }
      this._registryResolved = true;
      this._render();
      if (this.isConnected && !this._registryUnsubscribe && this._hass.connection?.subscribeEvents) {
        const unsubscribe = await this._hass.connection.subscribeEvents(() => {this._registryResolved=false;this._resolveRegistry();}, "entity_registry_updated");
        if (this.isConnected) this._registryUnsubscribe=unsubscribe;
        else unsubscribe();
      }
    } catch { /* Explicit mappings still work while the registry is unavailable. */ }
    finally { this._registryPending=false; }
  }
  connectedCallback() { this._registryResolved=false;this._resolveRegistry(); }
  disconnectedCallback() { this._registryUnsubscribe?.();this._registryUnsubscribe=null; }
}

if (!customElements.get("moon-practice-card")) customElements.define("moon-practice-card", MoonPracticeCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "moon-practice-card")) {
  window.customCards.push({ type: "moon-practice-card", name: "Daily Practice", description: "Affirmations, Tarot, Oracle, Gods, Runes, and cached daily horoscopes." });
}
