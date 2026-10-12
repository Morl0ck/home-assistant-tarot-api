/* HACS-installed sidebar panel. HA passes entity mappings from the registry. */
import "./moon-practice-card.js?v=1.4.1";

class TarotPracticePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
    this.shadowRoot.innerHTML = `<style>
      :host { display:block; height:100%; background:#111017; color:#f7f1eb; overflow:auto; }
      header { display:flex; align-items:center; gap:18px; position:sticky; top:0; z-index:10;
        height:56px; padding:0 20px; background:#19181f; border-bottom:1px solid #35313f;
        font:500 18px system-ui,sans-serif; }
      button { background:none; border:0; color:inherit; font-size:25px; width:40px; height:40px; cursor:pointer; }
      button:focus-visible { outline:2px solid #e9ad70; border-radius:8px; }
      button[hidden] { display:none; }
      main { max-width:520px; margin:28px auto; padding:0 12px;
        padding-bottom:env(safe-area-inset-bottom,0px); }
      @media(max-width:500px) { main { margin-top:16px; } }
    </style><header><button aria-label="Open sidebar" hidden>☰</button><span>Daily Practice</span></header><main></main>`;
    this._card = document.createElement("moon-practice-card");
    this.shadowRoot.querySelector("main").append(this._card);
    this.shadowRoot.querySelector("button").addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("hass-toggle-menu", {bubbles:true,composed:true}));
    });
  }

  set panel(panel) {
    const config = panel?.config?.card;
    if (!config) return;
    const signature = JSON.stringify(config);
    if (this._signature !== signature) {
      this._signature = signature;
      this._card.setConfig({type:"custom:moon-practice-card",...config});
    }
    if (this._hass) this._card.hass = this._hass;
  }

  set hass(hass) {
    this._hass = hass;
    this._card.hass = hass;
  }

  set narrow(narrow) {
    this.shadowRoot.querySelector("button").hidden = !narrow;
  }
}

if (!customElements.get("tarot-practice-panel")) customElements.define("tarot-practice-panel", TarotPracticePanel);
