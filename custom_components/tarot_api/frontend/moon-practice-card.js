/* Original bundled Home Assistant Practice card. No framework or CDN. */
const PRACTICE_TABS = [
  { key: "affirmation", label: "Affirmations", entity: "sensor.daily_affirmation", button: "button.new_affirmation", action: "Another affirmation" },
  { key: "tarot", label: "Tarot", entity: "sensor.tarot_card", button: "button.draw_tarot_card", action: "Draw a card" },
  { key: "oracle", label: "Oracle", entity: "sensor.oracle_card", button: "button.draw_oracle_card", action: "Draw a card" },
  { key: "deity", label: "Gods", entity: "sensor.deity_card", button: "button.draw_deity_card", action: "Draw a deity" },
  { key: "rune", label: "Runes", entity: "sensor.rune", button: "button.draw_rune", action: "Draw a rune" },
];
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
  :host { display:block; max-width:520px; margin-inline:auto; color:#f7f1eb; font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif); }
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
  @media(max-width:360px) { ha-card { padding:22px 14px 17px; } .reading { padding:22px 19px; } h1 { font-size:40px; } .tab { padding:12px 15px; } }
`;

class MoonPracticeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._active = "affirmation";
    this._errors = {};
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><ha-card>
      <header><div><p class="eyebrow">A little space for yourself</p><h1>Practice</h1></div><span class="header-moon" aria-hidden="true">☾</span></header>
      <nav class="tabs" role="tablist" aria-label="Practice sections"></nav>
      <section class="panel" id="practice-panel" role="tabpanel" aria-live="polite"></section>
      <footer>A moment to pause, a little room to grow.</footer></ha-card>`;
    const tabs = this.shadowRoot.querySelector(".tabs");
    tabs.innerHTML = PRACTICE_TABS.map((tab) => `<button class="tab" role="tab" id="tab-${tab.key}" data-tab="${tab.key}" aria-controls="practice-panel">${tab.label}</button>`).join("");
    this.shadowRoot.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-tab]");
      if (tab) this._select(tab.dataset.tab);
      if (event.target.closest("[data-draw]")) this._draw();
    });
    tabs.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const current = PRACTICE_TABS.findIndex((tab) => tab.key === this._active);
      const index = event.key === "Home" ? 0 : event.key === "End" ? 4 : (current + (event.key === "ArrowRight" ? 1 : -1) + 5) % 5;
      this._select(PRACTICE_TABS[index].key, true);
    });
  }

  setConfig(config) {
    if (config.default_tab && !PRACTICE_TABS.some((tab) => tab.key === config.default_tab)) throw new Error("Unknown default_tab. Use affirmation, tarot, oracle, deity, or rune.");
    const mappings = {};
    for (const tab of PRACTICE_TABS) {
      const mapping = config[tab.key] ?? {};
      const entity = mapping.entity ?? tab.entity;
      const button = mapping.button ?? tab.button;
      if (typeof entity !== "string" || !/^sensor\.[a-z0-9_]+$/.test(entity)) throw new Error(`${tab.label}: entity must be a sensor entity ID.`);
      if (typeof button !== "string" || !/^button\.[a-z0-9_]+$/.test(button)) throw new Error(`${tab.label}: button must be a button entity ID.`);
      mappings[tab.key] = { entity, button };
    }
    this._config = { ...config, ...mappings };
    this._active = config.default_tab || "affirmation";
    this._render();
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    if (!this._config) return;
    const mapping = this._config[this._active];
    const relevant = [mapping.entity, mapping.button, "sun.sun"];
    if (!previous || relevant.some((id) => previous.states[id] !== hass.states[id])) this._render();
  }

  getCardSize() { return 12; }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }
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
    for (const button of this.shadowRoot.querySelectorAll("[data-tab]")) {
      const selected = button.dataset.tab === this._active;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    }
    panel.setAttribute("aria-labelledby", `tab-${this._active}`);
    const waiting = this._busy === this._active;
    const canDraw = buttonAvailable(drawButton) && !this._busy;
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
    const restoreFocus = this.shadowRoot.activeElement?.hasAttribute("data-draw");
    const entityId = this._config[kind].button;
    if (!buttonAvailable(this._hass.states[entityId])) return;
    this._busy = kind;
    delete this._errors[kind];
    this._render();
    try {
      await this._hass.callService("button", "press", { entity_id: entityId });
    } catch (error) {
      this._errors[kind] = `Could not draw. ${error?.message || "Please try again."}`;
    } finally {
      this._busy = null;
      this._render();
      if (restoreFocus && this._active === kind) this.shadowRoot.querySelector("[data-draw]").focus({ preventScroll: true });
    }
  }
}

if (!customElements.get("moon-practice-card")) customElements.define("moon-practice-card", MoonPracticeCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "moon-practice-card")) {
  window.customCards.push({ type: "moon-practice-card", name: "Moon Practice", description: "Affirmations, Tarot, Oracle, Gods, and Runes in one calm daily practice." });
}
