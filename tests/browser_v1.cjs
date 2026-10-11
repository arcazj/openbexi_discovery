// Deterministic desktop/mobile acceptance. No scientific service or paid AI calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const {chromium} = require('playwright');
const {assertCaptions, assertCaptionFits} = require('./caption_helpers.cjs');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const record = {id:'pubmed:123456',source:'pubmed',type:'publication',title:'Fixture ovarian research',
  summary:'Fixture evidence for browser behavior; not a scientific claim.',url:'https://pubmed.ncbi.nlm.nih.gov/123456/',
  metadata:{abstract_available:true,retrieved_at:'2026-10-04T12:00:00Z'},year:'2025',authors:[]};
const candidate = {title:'Review ovarian outcomes',question:'Is ovarian reserve associated with outcomes?',
  population:'Unknown',exposure:'Ovarian reserve',outcome:'Reproductive outcomes',design:'Unknown',
  required_data:'Verify dataset',feasibility:'Unknown',uncertainties:'Verify with mentor',
  rationale:'Provisional fixture direction [pubmed:123456].',citations:[record.id]};
function result(payload){return {next_step:'Review the population for '+payload.query+' [pubmed:123456].',
  tip:'Check outcome availability before selecting a design.',refined_query:'ovarian reserve outcomes',
  explanation:'The retrieved record motivates a provisional direction [pubmed:123456].',candidate_question:candidate,
  citations:[{id:record.id,title:record.title,url:record.url}],evidence_ids:[record.id],
  model:'gpt-6.1-sol',prompt_version:'rei-evidence-1.1',generated_at:'2026-10-04T12:01:00Z',evidence_snapshot:payload};}
const server=http.createServer((req,res)=>{
  const name=new URL(req.url,'http://localhost').pathname.replace(/^\/hosted\//,'/');
  if(name==='/'||name==='/index.html'){
    res.setHeader('Content-Type','text/html; charset=utf-8');
    res.end(req.url.startsWith('/hosted/')?html.replace('<head>','<head><meta name="rei-hosted-demo" content="github-pages">'):html);
  }else if(['/assets/discovery.js','/assets/discovery.css','/assets/data.js','/assets/captions.js','/assets/customize.js','/assets/profile_ai.js','/assets/ai_progress.js'].includes(name)){res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':'text/css');res.end(fs.readFileSync(path.join(root,name.slice(1))));}else if(['/README.md','/HELP.md','/CHANGELOG.md'].includes(name))res.end(fs.readFileSync(path.join(root,name.slice(1))));
  else{res.statusCode=404;res.end('Not available');}
});
let browser, base, passed=0;
const pageErrors=[];
async function scenario(name,options,run){
  const context=await browser.newContext({viewport:options.viewport||{width:1365,height:950},reducedMotion:'reduce',hasTouch:!!options.touch});
  const page=await context.newPage();page.on('pageerror',e=>pageErrors.push(name+': '+e.message));
  const calls={guidance:[],api:[],queries:[],actions:[]};
  await page.route('**/api/**',async route=>{
    const req=route.request(),url=new URL(req.url());calls.api.push(url.pathname);
    const json=async body=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
    if(url.pathname==='/api/health')return json({version:'1.2.0',ai:{configured:options.connected!==false,model:'gpt-6.1-sol'}});
    if(url.pathname==='/api/ai/check')return json({accessible:true,model:'gpt-6.1-sol',message:'Fixture access verified'});
    if(url.pathname==='/api/search'){
      const payload=req.postDataJSON();calls.queries.push(payload.query);
      const records=options.empty?[]:options.mixed?[record,
        {...record,id:'ensembl:fixture',source:'ensembl',type:'gene',title:'Fixture gene annotation',url:'https://www.ensembl.org/'},
        {...record,id:'gwas:fixture',source:'gwas',type:'association',title:'Fixture trait association',url:'https://www.ebi.ac.uk/gwas/'}
      ]:Array.from({length:options.count||1},(_,i)=>({...record,id:'pubmed:'+(123456+i),url:'https://pubmed.ncbi.nlm.nih.gov/'+(123456+i)+'/'}));
      return json({query:payload.query,records,demo:false,
        interpretation:{type:'topic',term:payload.query},retrieved_at:'2026-10-04T12:00:00Z',
        coverage:payload.sources.map(source=>({source,status:source==='pubmed'||options.mixed?'ok':'skipped',total:source==='pubmed'||options.mixed?records.filter(r=>r.source===source).length:null,
          retrieved:records.filter(r=>r.source===source).length,truncated:false,query:payload.query,retrieved_at:'2026-10-04T12:00:00Z'}))});
    }
    if(url.pathname==='/api/ai'){
      const payload=req.postDataJSON();
      calls.actions.push(payload.action);
      if(payload.action!=='guidance')return json({text:'Fixture explanation [pubmed:123456].',citations:[record],candidate_questions:[candidate],model:'gpt-6.1-sol'});
      calls.guidance.push(payload);
      if(options.quota&&calls.guidance.length===1)return route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:{code:'insufficient_quota',message:'AI tokens are unavailable: your OpenAI API credits or quota are exhausted. Check your API billing or add credits, then retry.'}})});
      if(options.delay)await new Promise(resolve=>setTimeout(resolve,options.delay(payload,calls.guidance.length)));
      if(options.fail&&calls.guidance.length===1)return route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'AI temporarily unavailable. Retry suggestions.'})});
      if(options.malformed)return json({text:'Unsupported guidance'});
      return json(result(payload));
    }
    return route.fulfill({status:404,body:'Not available'});
  });
  try{
    await page.goto(base+(options.hosted?'/hosted/':'/'));
    await page.waitForFunction(()=>document.querySelector('#connection-label').textContent!== 'Checking AI');
    if(options.connected!==false&&!options.hosted)await page.waitForFunction(()=>document.querySelector('#connection-button').dataset.state==='ready');
    const search=async query=>{await page.locator('#query').fill(query);await page.locator('#search-button').click();await page.waitForFunction(()=>!document.querySelector('#result-actions').hidden);};
    const guided=async()=>page.waitForFunction(()=>document.querySelector('#guidance-phase').textContent==='AI guidance');
    await run({page,calls,search,guided});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'No horizontal overflow');
    passed++;console.log('PASS '+name);
  }finally{await context.close();}
}
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true});fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  await scenario('help captions with mouse and keyboard',{},async({page,search,guided})=>{
    await assertCaptions(page,'initial search');
    await page.locator('.interpret-organism').hover();await page.locator('#control-caption').waitFor({state:'visible'});
    assert.match(await page.locator('#control-caption').textContent(),/human genome.*Literature results may include other organisms/);
    await assertCaptionFits(page);await page.keyboard.press('Escape');
    await page.locator('#mode').selectOption('region');assert.match(await page.locator('#search-mode-caption').innerText(),/Genomic region.*GRCh38/);
    await page.locator('#mode').selectOption('auto');
    await page.locator('#query').focus();await page.keyboard.press('Tab');
    assert.equal(await page.locator('#search-button').evaluate(n=>n===document.activeElement),true);
    assert.match(await page.locator('#control-caption').innerText(),/Retrieve evidence/);
    await page.keyboard.press('Escape');assert.equal(await page.locator('#control-caption').isVisible(),false);
    await page.locator('#connection-button').click();await assertCaptions(page,'AI connection dialog');
    await page.locator('#ai-save-key').hover();await page.locator('#control-caption').waitFor({state:'visible'});
    assert.equal(await page.locator('#control-caption').evaluate(n=>n.closest('dialog')?.id),'ai-setup-dialog');
    await assertCaptionFits(page);await page.keyboard.press('Escape');assert.equal(await page.locator('#ai-setup-dialog').isVisible(),true,'Escape dismisses help before closing its dialog');
    await page.locator('[data-close="ai-setup-dialog"]').click();
    await search('ovarian aging');await guided();await assertCaptions(page,'search results and AI guidance');
    await page.getByRole('button',{name:'Inspect evidence',exact:true}).first().click();await assertCaptions(page,'source details');
    await page.locator('[data-close="detail-dialog"]').click();await page.locator('#new-question').click();await assertCaptions(page,'brief editor');
    await page.locator('[data-close="brief-dialog"]').first().click();await page.locator('#nav-help').click();await assertCaptions(page,'help topics');
  });
  await scenario('touch captions without activating buttons',{touch:true,viewport:{width:320,height:900}},async({page,calls})=>{
    await page.locator('#query').fill('ovarian aging');
    const target=await page.locator('#search-button').boundingBox(),cdp=await page.context().newCDPSession(page);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:target.x+target.width/2,y:target.y+target.height/2}]});
    await page.locator('#control-caption').waitFor({state:'visible'});await assertCaptionFits(page);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    assert.equal(calls.queries.length,0,'Press and hold explains the button without searching');
    await page.locator('#control-caption').waitFor({state:'visible'});
    await page.screenshot({path:path.join(root,'test-results/control-captions-mobile-320.png')});
    await page.locator('#search-button').tap();await page.waitForFunction(()=>state.search?.query==='ovarian aging');
    assert.equal(calls.queries.length,1,'An ordinary tap still performs the action once');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await cdp.detach();
  });
  for(const width of [1365,390,320])await scenario('compact layout and sticky controls '+width,{count:8,viewport:{width,height:950}},async({page,calls,search,guided})=>{
    assert.equal(await page.locator('#ai-connection-panel').count(),0);
    assert.equal(await page.locator('#connection-label').textContent(),'AI connected to GPT-6.1 Sol · key verified.');
    assert.equal(await page.locator('#app-version').textContent(),'V1.2.0');
    assert.equal(await page.locator('#results-heading').isVisible(),false,'No extra heading above the initial evidence card');
    const help=await page.locator('#nav-help').boundingBox(),settings=await page.locator('#connection-button').boundingBox();
    assert.ok(help.x>=settings.x+settings.width,'Help follows AI connection');
    assert.equal(help.y,settings.y,'Help shares the AI connection row');
    assert.equal(await page.locator('.site-header #nav-search,.site-header #nav-saved,.site-header #nav-library').count(),0);
    assert.equal(await page.locator('.brand>span').nth(1).isVisible(),true,'Brand name stays visible');
    const tip=await page.locator('#context-tip').evaluate(n=>({radius:getComputedStyle(n).borderRadius,border:getComputedStyle(n).borderTopWidth}));
    assert.equal(tip.radius,await page.locator('#guidance-card').evaluate(n=>getComputedStyle(n).borderRadius));
    assert.equal(tip.border,'1px');
    const field=page.locator('#query');
    await page.mouse.move(0,0);
    const fieldSize=await field.boundingBox(),defaultLine=await field.evaluate(n=>({border:getComputedStyle(n).borderTopWidth,shadow:getComputedStyle(n).boxShadow}));
    assert.equal(defaultLine.border,'1px','Query has a thin line by default');assert.ok(fieldSize.height>=44);
    await field.hover();
    assert.notEqual(await field.evaluate(n=>getComputedStyle(n).boxShadow),defaultLine.shadow,'Hover thickens the query line');
    await field.click();await page.mouse.move(0,0);
    assert.notEqual(await field.evaluate(n=>getComputedStyle(n).boxShadow),defaultLine.shadow,'Focus keeps the thicker line');
    const focusedSize=await field.boundingBox();
    assert.equal(focusedSize.width,fieldSize.width);assert.equal(focusedSize.height,fieldSize.height,'Focus does not shift the field');
    await field.evaluate(n=>n.blur());
    const position=await page.evaluate(()=>({source:document.querySelector('#source-strip').getBoundingClientRect().bottom,search:document.querySelector('.search-surface').getBoundingClientRect().top}));
    assert.ok(position.source<=position.search,'Sources above search');
    await search('ovarian aging');await guided();
    assert.equal(await page.locator('#results-heading').isVisible(),true,'Completed search keeps its result heading');
    assert.equal(await page.locator('#source-list-label').isVisible(),true,'Sources heading stays visible on mobile');
    const aiSurface=await page.locator('#guidance-card').evaluate(n=>getComputedStyle(n).backgroundImage);
    assert.equal(await page.locator('#context-tip').evaluate(n=>getComputedStyle(n).backgroundImage),aiSurface,'AI tip and next step share the soft surface');
    const presets=page.locator('.search-options .examples');
    assert.equal(await presets.count(),1,'Explore shares the Human / Auto-detect section');
    assert.equal(await page.locator('.search-surface #recent').count(),0,'Recent is outside the search panel');
    assert.equal(await presets.locator('span').textContent(),'Explore:');
    const exploreLabel=await presets.locator('span').boundingBox(),recentLabel=await page.locator('#recent>span').boundingBox();
    assert.ok(Math.abs(exploreLabel.x-recentLabel.x)<=2,'Recent: starts directly beneath Explore:');
    assert.ok(recentLabel.y>=exploreLabel.y+exploreLabel.height,'Recent is below Explore');
    await page.mouse.move(0,0);
    assert.equal(await page.locator('#suggest-questions').evaluate(n=>getComputedStyle(n).backgroundImage),await page.locator('#connection-button').evaluate(n=>getComputedStyle(n).backgroundImage),'AI status and directions share the orange-grey palette');
    assert.notEqual(aiSurface,await page.locator('#suggest-questions').evaluate(n=>getComputedStyle(n).backgroundImage),'AI text uses a softer surface than action buttons');
    assert.equal(await page.locator('#mode').evaluate(n=>getComputedStyle(n).backgroundImage),await presets.locator('button').first().evaluate(n=>getComputedStyle(n).backgroundImage),'Auto-detect matches the grey presets');
    const controls=await page.evaluate(()=>['search-button','research-more','suggest-questions'].map(id=>{
      const r=document.getElementById(id).getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};
    }));
    assert.ok(controls[0].right<=controls[1].left&&controls[1].right<=controls[2].left,'Search, More actions, then Suggest research directions');
    assert.ok(Math.max(...controls.map(r=>r.top))<Math.min(...controls.map(r=>r.bottom)),'Actions share a row');
    assert.equal(await page.locator('#search-button').getAttribute('class'),'');
    assert.ok((await page.locator('#suggest-questions').getAttribute('class')).includes('primary'));
    assert.equal(await page.locator('#make-question').isVisible(),false);
    await page.locator('#research-more summary').click();assert.equal(await page.locator('#make-question').isVisible(),true);
    await page.keyboard.press('Escape');
    await page.evaluate(()=>window.scrollTo(0,window.scrollY+document.querySelector('#source-strip').getBoundingClientRect().top+60));
    const dock=await page.evaluate(()=>({source:document.querySelector('#source-strip').getBoundingClientRect(),actions:document.querySelector('#result-actions').getBoundingClientRect()}));
    assert.ok(dock.source.top>=0&&dock.source.top<=13);assert.ok(dock.actions.top>=dock.source.bottom);
    await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(root,'test-results','v1-'+width+'.png'),fullPage:true});
    if(width<650){assert.equal(await page.locator('#connection-short-label').isVisible(),true);await page.locator('#connection-button').click();assert.match(await page.locator('#ai-setup-note').textContent(),/gpt-6.1-sol.*key verified/);}
    if(width===1365){
      await page.locator('#suggest-questions').click();await page.waitForFunction(()=>!state.aiController&&document.querySelector('#ai-output .candidate'));
      assert.ok(calls.actions.includes('questions'),'Directions still invokes AI');
      assert.equal(calls.queries.length,1,'Directions does not submit the search form');
      assert.equal(await page.locator('#ai-output .ai-box').evaluate(n=>getComputedStyle(n).backgroundImage),aiSurface);
      assert.equal(await page.locator('#ai-output .candidate').evaluate(n=>getComputedStyle(n).backgroundImage),aiSurface);
    }
  });
  await scenario('saved research remains accessible through hosted settings',{hosted:true,connected:false},async({page})=>{
    assert.equal(await page.locator('.intro h1').textContent(),'Your fellowship research workspace');
    assert.equal(await page.locator('.intro p').textContent(),'Explore topics, genes, or genomic regions to find evidence and shape your next question.');
    await page.locator('#profile-settings').click();await page.locator('#profile-dialog[open]').waitFor();
    assert.equal(await page.locator('#profile-dialog h2').textContent(),'Settings');
    assert.equal(await page.locator('#nav-library').isDisabled(),true,'Hosted library requires the local app');
    await page.getByRole('button',{name:'Open saved research',exact:true}).click();
    await page.locator('#saved-page').waitFor({state:'visible'});
    await page.locator('#saved-new').click();await page.locator('#brief-title').fill('Saved navigation check');await page.locator('#brief-question').fill('Can I reopen this brief from Settings?');
    await page.locator('#brief-form button[type=submit]').click();
    await page.locator('.brand').click();await page.locator('#search-page').waitFor({state:'visible'});
    await page.locator('#profile-settings').click();await page.getByRole('button',{name:'Open saved research',exact:true}).click();
    assert.ok((await page.locator('#saved-list').innerText()).includes('Saved navigation check'));
    await page.reload();await page.locator('#search-page').waitFor({state:'visible'});assert.equal(await page.locator('#saved-page').isVisible(),false,'Search is the default after reload');
    await page.getByRole('button',{name:'Help',exact:true}).click();await page.locator('#help-dialog[open]').waitFor();
  });
  await scenario('source palettes stay consistent from selection to evidence',{mixed:true},async({page,search,guided})=>{
    await search('ovarian aging');await guided();
    await page.mouse.move(0,0);
    const palettes=[];
    for(const source of ['pubmed','ensembl','gwas']){
      const selected=await page.locator('.source-chip[data-source="'+source+'"]').evaluate(n=>({background:getComputedStyle(n).backgroundImage,border:getComputedStyle(n).borderColor}));
      const card=page.locator('.record[data-source="'+source+'"]');
      assert.equal(await card.count(),1);
      assert.equal(await card.evaluate(n=>getComputedStyle(n).borderColor),selected.border);
      assert.equal(await card.locator('.tag[data-source]').evaluate(n=>getComputedStyle(n).backgroundImage),selected.background);
      assert.equal(await page.locator('.coverage-item[data-source="'+source+'"]').evaluate(n=>getComputedStyle(n).backgroundImage),selected.background);
      palettes.push(selected.background);
    }
    assert.equal(new Set(palettes).size,3,'Each source has its own color');
    assert.notEqual(await page.locator('#evidence-area').evaluate(n=>getComputedStyle(n).backgroundImage),await page.locator('.record').first().evaluate(n=>getComputedStyle(n).backgroundImage));
    await page.locator('.record[data-source="pubmed"] h3 button').click();
    assert.equal(await page.locator('#detail-body .tag[data-source="pubmed"]').evaluate(n=>getComputedStyle(n).backgroundImage),palettes[0]);
  });
  await scenario('guidance cache, changed context and no keystroke calls',{},async({page,calls,search,guided})=>{
    await search('ovarian aging');await guided();assert.equal(calls.guidance.length,1);
    await page.locator('#query').fill('different topic');assert.equal(calls.guidance.length,1);assert.match(await page.locator('#guidance-phase').textContent(),/search again/);
    await page.locator('#query').fill('ovarian aging');assert.equal(await page.locator('#guidance-phase').textContent(),'AI guidance');
    await search('ovarian aging');await guided();assert.equal(calls.guidance.length,1,'Reuse same evidence/context');
    await page.locator('#constraints summary').click();await page.locator('#constraint-data').fill('Clinic registry');await page.locator('#constraint-data').blur();await guided();
    assert.equal(calls.guidance.length,2);assert.equal(calls.guidance[1].constraints.data,'Clinic registry');
    await page.locator('#guidance-refresh').click();await guided();assert.equal(calls.guidance.length,3);
    await page.locator('#guidance-why summary').click();assert.equal(await page.locator('#guidance-citations a').getAttribute('href'),record.url);
  });
  await scenario('save proposal, add note and preserve both audits',{},async({page,calls,search,guided})=>{
    await search('ovarian aging');await guided();await page.locator('#guidance-save').click();
    assert.equal(await page.locator('#brief-question').inputValue(),candidate.question);
    const aiSurface=await page.locator('#guidance-card').evaluate(n=>getComputedStyle(n).backgroundImage);
    assert.equal(await page.locator('#brief-question').evaluate(n=>getComputedStyle(n).backgroundImage),aiSurface,'AI-generated brief is highlighted while editing');
    await page.locator('#brief-form button[type=submit]').click();await guided();
    assert.equal(calls.guidance.at(-1).questions[0].question,candidate.question);
    await page.locator('#guidance-add').click();await page.locator('#next-step-briefs button').filter({hasText:candidate.title}).click();
    assert.match(await page.locator('#brief-notes').inputValue(),/AI next step/);
    await page.locator('#brief-form button[type=submit]').click();await guided();
    const workspace=await page.evaluate(()=>JSON.parse(localStorage.getItem('rei-research-workspace-v1')));
    assert.equal(workspace.app_version,'1.2.0');assert.equal(workspace.questions[0].ai_audit.action,'guidance');
    assert.equal(workspace.questions[0].guidance_audits.length,1);assert.equal(workspace.questions[0].guidance_audits[0].evidence_snapshot.records[0].id,record.id);
    assert.equal(await page.locator('.saved-card[data-ai-assisted="true"]').evaluate(n=>getComputedStyle(n).backgroundImage),aiSurface,'Saved AI-assisted question keeps the soft surface');
    await page.locator('#guidance-query').click();await guided();assert.equal(calls.queries.at(-1),'ovarian reserve outcomes');
  });
  await scenario('automatic guidance off and explicit refresh',{},async({page,calls,search,guided})=>{
    await page.locator('#connection-button').click();await page.locator('#ai-guidance-preferences').click();await page.locator('#automatic-guidance').uncheck();await page.locator('[data-close="help-dialog"]').click();
    await search('ovarian aging');assert.equal(calls.guidance.length,0);assert.match(await page.locator('#guidance-phase').textContent(),/manual guidance/);
    await page.locator('#guidance-refresh').click();await guided();assert.equal(calls.guidance.length,1);
  });
  await scenario('AI failure preserves evidence and manual brief; retry works',{fail:true},async({page,calls,search,guided})=>{
    await search('ovarian aging');await page.waitForFunction(()=>document.querySelector('#guidance-phase').textContent.includes('retry'));
    assert.equal(await page.locator('.record').count(),1);assert.equal(await page.locator('#guidance-actions').isVisible(),false);
    await page.locator('#research-more summary').click();await page.locator('#make-question').click();assert.equal(await page.locator('#brief-dialog').isVisible(),true);
    await page.getByRole('button',{name:'Close research brief',exact:true}).click();await page.locator('#guidance-refresh').click();await guided();assert.equal(calls.guidance.length,2);
  });
  await scenario('quota exhaustion stays visible until generation succeeds',{quota:true},async({page,calls,search,guided})=>{
    await search('ovarian aging');await page.locator('#ai-availability-notice').waitFor({state:'visible'});
    assert.match(await page.locator('#ai-availability-notice').textContent(),/credits or quota are exhausted/);
    assert.equal(await page.locator('#connection-label').textContent(),'AI tokens unavailable');
    await page.locator('#connection-button').click();assert.equal(await page.locator('#ai-setup-dialog [data-ai-availability]').isVisible(),true);
    await page.locator('#ai-retry-connection').click();await page.waitForFunction(()=>state.aiStatus?.phase==='ready');
    assert.equal(await page.locator('#ai-setup-dialog [data-ai-availability]').isVisible(),true,'Model access does not prove that quota was replenished');
    await page.getByRole('button',{name:'Close AI setup',exact:true}).click();
    await search('PCOS');assert.equal(calls.guidance.length,1,'Exhausted quota prevents automatic retries');
    await page.locator('#guidance-refresh').click();await guided();
    assert.equal(await page.locator('#ai-availability-notice').isVisible(),false);
    assert.match(await page.locator('#connection-label').textContent(),/^AI connected/);
    assert.equal(await page.locator('#connection-button').evaluate(node=>node.classList.contains('d-budget-blocked')),false);
  });
  await scenario('malformed guidance uses labeled fallback',{malformed:true},async({page,search})=>{
    await search('ovarian aging');await page.waitForFunction(()=>document.querySelector('#guidance-phase').textContent.includes('retry'));
    assert.equal(await page.locator('#guidance-actions').isVisible(),false);assert.equal(await page.locator('.record').count(),1);
  });
  await scenario('stale and canceled guidance cannot replace current context',{delay:(p,n)=>n===2?20:700},async({page,calls,search,guided})=>{
    await search('ovarian aging');await page.waitForFunction(()=>document.querySelector('#guidance-cancel').hidden===false);
    await search('PCOS');await guided();assert.match(await page.locator('#guidance-next').textContent(),/PCOS/);
    await page.waitForTimeout(750);assert.match(await page.locator('#guidance-next').textContent(),/PCOS/);
    await page.locator('#guidance-refresh').click();await page.locator('#guidance-cancel').click();
    assert.match(await page.locator('#guidance-next').textContent(),/cancelled/);assert.equal(await page.locator('#guidance-actions').isVisible(),false);
  });
  await scenario('missing key and illustrative evidence never trigger AI',{connected:false},async({page,calls,search})=>{
    await search('ovarian aging');assert.equal(calls.guidance.length,0);assert.match(await page.locator('#guidance-phase').textContent(),/unavailable/);
    await page.locator('#guidance-refresh').click();assert.equal(await page.locator('#ai-setup-dialog').isVisible(),true);await page.locator('[data-close="ai-setup-dialog"]').click();
    await page.locator('#demo-button').click();assert.equal(calls.guidance.length,0);assert.match(await page.locator('#guidance-phase').textContent(),/example mode/);assert.equal(await page.locator('#suggest-questions').isDisabled(),true);
  });
  await scenario('empty search never generates scientific guidance',{empty:true},async({page,calls,search})=>{
    await search('ovarian aging');assert.equal(calls.guidance.length,0);assert.match(await page.locator('#guidance-phase').textContent(),/no evidence/);
  });
  await scenario('hosted demo has fallback and no backend/key requests',{hosted:true},async({page,calls})=>{
    assert.equal(calls.api.length,0);await page.locator('#connection-button').click();
    assert.equal(await page.locator('#ai-setup-form').isVisible(),false);await page.locator('#ai-connection-help').click();
    assert.match(await page.locator('#help-content').textContent(),/private local backend/);
    await page.locator('[data-close="help-dialog"]').click();await page.locator('#demo-button').click();assert.equal(calls.api.length,0);
  });
  assert.deepEqual(pageErrors,[]);console.log(`${passed} browser scenarios passed; no page errors.`);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{await browser?.close();server.close();});
