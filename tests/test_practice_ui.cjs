/* Optional browser checks: NODE_PATH must include an installed playwright. */
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const http=require('node:http');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const mime={'.js':'text/javascript','.json':'application/json','.html':'text/html','.png':'image/png'};
(async()=>{
  const server=http.createServer(async(req,res)=>{
    const file=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);
    if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
    try {const data=await fs.readFile(file);res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.end(data);}
    catch {res.writeHead(404).end();}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    const url=`http://127.0.0.1:${server.address().port}/examples/moon_practice_preview.html`;
    await page.goto(url);await page.locator('moon-practice-card .hero h2').waitFor();
    const layout=()=>page.locator('moon-practice-card .panel').evaluate(el=>({columns:getComputedStyle(el).gridTemplateColumns,width:el.getBoundingClientRect().width,overflow:el.scrollWidth>el.clientWidth}));
    let geometry=await layout();assert.equal(geometry.columns.split(' ').length,2);assert(geometry.width>1000);assert.equal(geometry.overflow,false);
    assert.equal(await page.locator('moon-practice-card .tabs').isVisible(),false);
    const name=await page.locator('moon-practice-card .hero h2').textContent();
    await page.locator('moon-practice-card [data-draw]').click();
    assert.notEqual(await page.locator('moon-practice-card .hero h2').textContent(),name);
    if(process.env.UI_SCREENSHOTS) await page.screenshot({path:path.join(process.env.UI_SCREENSHOTS,'daily-practice-desktop.png'),fullPage:true});
    for(const title of ['Tarot','Oracle','Gods','Runes','Horoscopes']){
      await page.getByRole('tab',{name:title,exact:true}).click();
      assert.equal(await page.locator('moon-practice-card h1').textContent(),title);
    }
    await page.locator('moon-practice-card [data-sign="pisces"]').click();
    assert.match(await page.locator('moon-practice-card .horoscope-heading').textContent(),/Pisces/);
    await page.reload();await page.getByRole('tab',{name:'Horoscopes',exact:true}).click();
    assert.match(await page.locator('moon-practice-card .horoscope-heading').textContent(),/Pisces/);
    if(process.env.UI_SCREENSHOTS) await page.screenshot({path:path.join(process.env.UI_SCREENSHOTS,'daily-horoscopes-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    geometry=await layout();assert.equal(geometry.columns.split(' ').length,1);assert.equal(geometry.overflow,false);
    await page.locator('moon-practice-card [data-sign-select]').selectOption('leo');
    assert.match(await page.locator('moon-practice-card .horoscope-heading').textContent(),/Leo/);
    if(process.env.UI_SCREENSHOTS) await page.screenshot({path:path.join(process.env.UI_SCREENSHOTS,'daily-horoscopes-phone.png'),fullPage:true});
    await page.getByRole('tab',{name:'Tarot',exact:true}).click();
    await page.locator('moon-practice-card img').evaluate(img=>img.decode());
    await page.goto(url+'?tab=horoscope&scenario=horoscope-outage');
    await page.locator('moon-practice-card .status').waitFor();
    assert.match(await page.locator('moon-practice-card .status').first().textContent(),/last saved reading/);
    await page.goto(url+'?tab=horoscope&scenario=horoscope-empty');
    await page.locator('moon-practice-card .horoscope-heading').waitFor();
    assert.match(await page.locator('moon-practice-card .reading').textContent(),/Latest reading unavailable/);
    await page.goto(url+'?tab=horoscope&scenario=escaped');
    await page.locator('moon-practice-card [data-sign-select]').selectOption('aries');
    assert.equal(await page.locator('moon-practice-card .reading img').count(),0);
    assert.match(await page.locator('moon-practice-card .reading').textContent(),/<img src=x/);
    await page.goto(url+'?legacy=1');
    await page.locator('moon-practice-card .tabs').waitFor();
    await page.locator('moon-practice-card [data-tab="affirmation"]').focus();
    await page.keyboard.press('End');
    assert.equal(await page.locator('moon-practice-card [data-tab="horoscope"]').getAttribute('aria-selected'),'true');
    await page.goto(url);
    await page.locator('moon-practice-card .hero h2').waitFor();
    await page.evaluate(async()=>{
      const card=document.querySelector('moon-practice-card');
      const sample=card._hass.states['sensor.daily_affirmation'];
      window.registryRows=[{config_entry_id:'test-entry',platform:'tarot_api',unique_id:'test-uid_practice_affirmation',entity_id:'sensor.first_name'}];
      window.registryRemoved=0;
      card.setConfig({section:'affirmation',entry_id:'test-entry',unique_prefix:'test-uid'});
      card.hass={states:{'sensor.first_name':sample},callWS:async()=>window.registryRows,
        connection:{subscribeEvents:async(callback)=>{window.registryChanged=callback;return()=>window.registryRemoved++;}}};
      await new Promise(resolve=>setTimeout(resolve,30));
      if(card._config.affirmation.entity!=='sensor.first_name')throw Error('Initial registry mapping failed');
      window.registryRows[0].entity_id='sensor.renamed_affirmation';
      card.hass={...card._hass,states:{'sensor.renamed_affirmation':sample}};
      window.registryChanged();await new Promise(resolve=>setTimeout(resolve,30));
      if(card._config.affirmation.entity!=='sensor.renamed_affirmation')throw Error('Entity rename was not followed');
      window.registryRows=[];window.registryChanged();await new Promise(resolve=>setTimeout(resolve,30));
      if(card._config.affirmation.entity!=='sensor.tarot_api_missing_affirmation')throw Error('Removed entity leaked another entry default');
      card.remove();
      if(window.registryRemoved!==1)throw Error('Registry subscription leaked on removal');
    });
    assert.deepEqual(errors,[]);
    console.log('Desktop/mobile layout, all sections, redraw, sign persistence, artwork, outages, escaping and keyboard checks passed.');
  } finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exit(1);});
