/* First-open migration to a persistent, editable native Lovelace dashboard. */
import "./moon-practice-card.js?v=1.5.0";
import {ensureDashboard} from "./practice-dashboard.js?v=1.5.0";
class TarotPracticePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
    this.shadowRoot.innerHTML = `<style>
      :host {display:block; padding:32px; color:var(--primary-text-color);}
      main {max-width:700px; margin:24px auto;}
      p {line-height:1.7; white-space:pre-line;}
      button {font:inherit; padding:12px 20px; min-height:44px; cursor:pointer;}
    </style><main><h1>Daily Practice</h1><p role="status">Opening your dashboard…</p><button hidden>Try again</button></main>`;
    this.shadowRoot.querySelector("button").addEventListener("click",()=>{this._started=false;this._open();});
  }
  set panel(panel) {this._panel=panel;this._open();}
  set hass(hass) {this._hass=hass;this._open();}
  async _open() {
    if(this._started || !this._hass || !this._panel?.config) return;
    this._started=true;
    const status=this.shadowRoot.querySelector("p");
    const button=this.shadowRoot.querySelector("button");
    button.hidden=true;
    try {
      const path=await ensureDashboard(this._hass,this._panel.config,text=>{status.textContent=text;});
      window.location.replace(`/${path}/affirmation`);
    } catch(error) {
      status.textContent=error?.message || "Could not open Daily Practice. Please try again.";
      button.hidden=false;
    }
  }
}
if(!customElements.get("tarot-practice-panel")) customElements.define("tarot-practice-panel",TarotPracticePanel);
