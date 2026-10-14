import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const source=await readFile(new URL("../custom_components/tarot_api/frontend/practice-dashboard.js",import.meta.url),"utf8");
const {dashboardConfig,ensureDashboard}=await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const config={dashboard_path:"daily-practice-test",tarot_api_entry_id:"test",unique_prefix:"test-uid",card:{horoscope:{entity:"sensor.renamed",button:"button.renamed"}}};
const generated=dashboardConfig(config);
assert.equal(generated.views.length,6);
assert.deepEqual(generated.views.map(v=>v.path),["affirmation","tarot","oracle","deity","rune","horoscope"]);
assert(generated.views.every(v=>v.type==="sections" && v.sections[0].column_span===3));
assert.equal(generated.views.at(-1).sections[0].cards[0].horoscope.entity,"sensor.renamed");
const calls=[];
let saved;
const hass={user:{is_admin:true},async callWS(msg){
  calls.push(msg.type);
  if(msg.type==="lovelace/dashboards/list") return saved?[{url_path:config.dashboard_path}]:[];
  if(msg.type==="lovelace/config/save") {saved=msg.config;return;}
  if(msg.type==="lovelace/config") return saved;
}};
assert.equal(await ensureDashboard(hass,config),config.dashboard_path);
assert.equal(calls.filter(c=>c==="lovelace/config/save").length,1);
saved.views[0].title="My custom title";
await ensureDashboard(hass,config);
assert.equal(saved.views[0].title,"My custom title");
assert.equal(calls.filter(c=>c==="lovelace/config/save").length,1);
const regular={user:{is_admin:false},callWS:async()=>{throw new Error("config_not_found");}};
await assert.rejects(()=>ensureDashboard(regular,config),/administrator/);
assert.equal(await ensureDashboard({user:{is_admin:false},callWS:async()=>({views:[]})},config),config.dashboard_path);
let listed=0;
const racing={user:{is_admin:true},async callWS(msg){
  if(msg.type==="lovelace/dashboards/list") return listed++?[{url_path:config.dashboard_path}]:[];
  if(msg.type==="lovelace/dashboards/create") throw new Error("Already exists");
  if(msg.type==="lovelace/config") return {views:[{title:"Other browser edits"}]};
  throw new Error("Must not overwrite concurrent config");
}};
assert.equal(await ensureDashboard(racing,config),config.dashboard_path);
const failedSave={user:{is_admin:true},async callWS(msg){
  if(msg.type==="lovelace/dashboards/list") return [];
  if(msg.type==="lovelace/config/save") throw new Error("Disk full");
}};
await assert.rejects(()=>ensureDashboard(failedSave,config),/starting layout could not be saved/);
console.log("Native dashboard creation, preservation, permissions, concurrency and failure checks passed.");
