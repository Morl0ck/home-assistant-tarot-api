/* Optional browser checks: NODE_PATH must include an installed playwright. */
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const http=require('node:http');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const mime={'.js':'text/javascript','.json':'application/json','.html':'text/html','.png':'image/png'};
(async()=>{
  let cachedProxyRequests=0;
  const server=http.createServer(async(req,res)=>{
    const requested=new URL(req.url,'http://localhost');
    let file=path.resolve(root,'.'+requested.pathname);
    if(requested.pathname==='/api/image_proxy/image.preview'){
      cachedProxyRequests++;
      res.setHeader('Cache-Control','private, max-age=3600');
      file=path.join(root,'custom_components/tarot_api/artwork/mother_nature',requested.searchParams.get('v')==='queen'?'pequ.png':'sw03.png');
    }
    if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
    try {const data=await fs.readFile(file);res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.end(data);}
    catch {res.writeHead(404).end();}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',error=>{errors.push(error.message);console.error(error.message);});
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
    for(const width of [1440,390]) {
      await page.setViewportSize({width,height:900});
      for(const [title,kind] of [['Affirmations','affirmation'],['Oracle','oracle'],['Gods','deity'],['Runes','rune']]) {
        await page.getByRole('tab',{name:title,exact:true}).click();
        const previous=await page.locator('moon-practice-card .hero h2').textContent();
        await page.locator('moon-practice-card [data-draw]').click();
        const expected=await page.evaluate(kind=>{
          const card=document.querySelector('moon-practice-card');
          return card._hass.states[card._config[kind].entity].attributes;
        },kind);
        assert.equal(await page.locator('moon-practice-card .hero h2').textContent(),expected.name);
        assert.notEqual(expected.name,previous);
        assert.equal(await page.locator('moon-practice-card .reading > p').first().textContent(),expected.interpretation);
        assert.equal(await page.locator('moon-practice-card img').count(),0);
        if(kind!=='affirmation')assert.equal(await page.locator('moon-practice-card .symbol').textContent(),expected.symbol);
        else assert.equal(await page.locator('moon-practice-card .landscape').count(),1);
        // Exercise an automatic entity update, without clicking or refreshing.
        await page.evaluate(kind=>{
          const card=document.querySelector('moon-practice-card'),previous=card._hass,id=card._config[kind].entity;
          const entity=previous.states[id];
          card.hass={...previous,states:{...previous.states,[id]:{...entity,attributes:{...entity.attributes,name:'Updated daily practice',interpretation:'Updated reading',symbol:'✧'}}}};
        },kind);
        assert.equal(await page.locator('moon-practice-card .hero h2').textContent(),'Updated daily practice');
        assert.equal(await page.locator('moon-practice-card .reading > p').first().textContent(),'Updated reading');
        if(kind!=='affirmation')assert.equal(await page.locator('moon-practice-card .symbol').textContent(),'✧');
      }
      await page.getByRole('tab',{name:'Affirmations',exact:true}).click();
      await page.evaluate(()=>{const card=document.querySelector('moon-practice-card'),previous=card._hass;card.hass={...previous,states:{...previous.states,'sun.sun':{state:'above_horizon',attributes:{}}}};});
      assert.equal(await page.locator('moon-practice-card .hero.day').count(),1);
      await page.evaluate(()=>{const card=document.querySelector('moon-practice-card'),previous=card._hass;card.hass={...previous,states:{...previous.states,'sun.sun':{state:'below_horizon',attributes:{}}}};});
      assert.equal(await page.locator('moon-practice-card .hero.day').count(),0);
      await page.getByRole('tab',{name:'Horoscopes',exact:true}).click();
      for(const sign of ['aries','pisces','leo']) {
        if(width<700)await page.locator('moon-practice-card [data-sign-select]').selectOption(sign);
        else await page.locator(`moon-practice-card [data-sign="${sign}"]`).click();
        const expected=await page.evaluate(sign=>{
          const card=document.querySelector('moon-practice-card');return card._hass.states[card._config.horoscope.entity].attributes.readings[sign].interpretation;
        },sign);
        assert.equal(await page.locator('moon-practice-card .reading > p').nth(1).textContent(),expected);
        assert.equal(await page.locator('moon-practice-card img').count(),0);
      }
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.getByRole('tab',{name:'Tarot',exact:true}).click();
    await page.locator('moon-practice-card [data-card-count="3"]').click();
    assert.equal(await page.getByRole('button',{name:'Draw three cards',exact:true}).count(),1);
    assert.match(await page.locator('moon-practice-card .empty').textContent(),/little more perspective/);
    await page.locator('moon-practice-card [data-draw]').click();
    assert.equal(await page.locator('moon-practice-card .spread-card').count(),3);
    assert.deepEqual(await page.locator('moon-practice-card .position').allTextContents(),['Past','Present','Future']);
    assert.equal(await page.locator('moon-practice-card .art.reversed').count(),1);
    for(const img of await page.locator('moon-practice-card .spread-card img').all()) await img.evaluate(el=>el.decode());
    let spreadGeometry=await layout();assert.equal(spreadGeometry.columns.split(' ').length,3);assert.equal(spreadGeometry.overflow,false);
    const spreadNames=await page.locator('moon-practice-card .spread-card h2').allTextContents();
    assert.equal(new Set(spreadNames).size,3);
    if(process.env.UI_SCREENSHOTS) await page.screenshot({path:path.join(process.env.UI_SCREENSHOTS,'tarot-three-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    spreadGeometry=await layout();assert.equal(spreadGeometry.columns.split(' ').length,1);assert.equal(spreadGeometry.overflow,false);
    if(process.env.UI_SCREENSHOTS) await page.screenshot({path:path.join(process.env.UI_SCREENSHOTS,'tarot-three-phone.png'),fullPage:true});
    await page.locator('moon-practice-card [data-card-count="1"]').click();
    assert.equal(await page.locator('moon-practice-card .spread-card').count(),0);
    await page.locator('moon-practice-card [data-draw]').click();
    await page.locator('moon-practice-card [data-card-count="3"]').click();
    assert.deepEqual(await page.locator('moon-practice-card .spread-card h2').allTextContents(),spreadNames);
    assert.equal(await page.getByRole('button',{name:'Draw three cards',exact:true}).count(),1);
    await page.locator('moon-practice-card [data-draw]').click();
    assert.notDeepEqual(await page.locator('moon-practice-card .spread-card h2').allTextContents(),spreadNames);
    await page.setViewportSize({width:1440,height:1000});
    await page.getByRole('tab',{name:'Horoscopes',exact:true}).click();
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
    await page.evaluate(()=>{
      const card=document.querySelector('moon-practice-card'),previous=card._hass;
      const sensor={state:'Queen of Pentacles',attributes:{card_name:'Queen of Pentacles',orientation:'upright',artwork_url:'/api/image_proxy/image.preview?token=constant&v=queen'}};
      card.hass={...previous,states:{...previous.states,'sensor.tarot_card':sensor}};
    });
    await page.locator('moon-practice-card img').evaluate(img=>img.decode());
    assert.equal(cachedProxyRequests,1);
    await page.evaluate(()=>{
      const card=document.querySelector('moon-practice-card'),previous=card._hass;
      const sensor={state:'Three of Swords',attributes:{card_name:'Three of Swords',orientation:'upright',artwork_url:'/api/image_proxy/image.preview?token=constant&v=swords'}};
      card.hass={...previous,states:{...previous.states,'sensor.tarot_card':sensor}};
    });
    await page.locator('moon-practice-card img').evaluate(img=>img.decode());
    assert.equal(cachedProxyRequests,2);
    assert.equal(await page.locator('moon-practice-card .hero h2').textContent(),'Three of Swords');
    assert.match(await page.locator('moon-practice-card img').getAttribute('src'),/token=constant&v=swords/);
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
    await page.goto(url+'?tab=tarot&scenario=spread-escaped');
    await page.locator('moon-practice-card [data-card-count="3"]').click();
    await page.locator('moon-practice-card [data-draw]').click();
    assert.match(await page.locator('moon-practice-card .spread-card h2').first().textContent(),/<img src=x/);
    assert.equal(await page.locator('moon-practice-card .spread-card').first().locator('img').count(),0);
    assert.equal(await page.locator('moon-practice-card .spread-card script').count(),0);
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
