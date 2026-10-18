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
  }else if(['/assets/discovery.js','/assets/discovery.css','/assets/search.js','/assets/search.css','/assets/data.js','/assets/captions.js','/assets/customize.js','/assets/profile_ai.js','/assets/ai_progress.js'].includes(name)){res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':'text/css');res.end(fs.readFileSync(path.join(root,name.slice(1))));}else if(['/README.md','/HELP.md','/CHANGELOG.md'].includes(name))res.end(fs.readFileSync(path.join(root,name.slice(1))));
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
    if(url.pathname==='/api/health')return json({version:'1.2.2',ai:{configured:options.connected!==false,model:'gpt-6.1-sol'}});
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
      if(payload.action!=='guidance')return json({text:'Fixture explanation [pubmed:123456].',citations:[record],candidate_questions:payload.action==='questions'?[candidate]:[],model:'gpt-6.1-sol'});
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
    const search=async query=>{await page.locator('#query').fill(query);await page.locator('#specific-search-button').click();await page.waitForFunction(query=>!state.searchController&&state.search?.query===query,query);};
    const newBrief=async()=>{await page.getByRole('button',{name:'Saved research',exact:true}).click();await page.locator('#saved-new').click();};
    await run({page,calls,search,newBrief});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'No horizontal overflow');
    passed++;console.log('PASS '+name);
  }finally{await context.close();}
}
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true});fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  await scenario('help captions with mouse and keyboard',{},async({page,search,newBrief})=>{
    await assertCaptions(page,'initial search');
    await page.locator('#query').focus();await page.keyboard.press('Tab');
    assert.equal(await page.locator('#search-button').evaluate(n=>n===document.activeElement),true);
    assert.match(await page.locator('#control-caption').innerText(),/Search broadly/);
    await assertCaptionFits(page);await page.keyboard.press('Escape');
    await page.locator('#connection-button').click();await assertCaptions(page,'AI connection dialog');
    await page.locator('#ai-save-key').hover();await page.locator('#control-caption').waitFor({state:'visible'});
    assert.equal(await page.locator('#control-caption').evaluate(n=>n.closest('dialog')?.id),'ai-setup-dialog');
    await assertCaptionFits(page);await page.keyboard.press('Escape');
    assert.equal(await page.locator('#ai-setup-dialog').isVisible(),true);
    await page.locator('[data-close="ai-setup-dialog"]').click();
    await search('ovarian aging');await assertCaptions(page,'search results');
    await page.getByRole('button',{name:'Inspect evidence',exact:true}).first().click();await assertCaptions(page,'source details');
    assert.ok((await page.locator('#detail-dialog').boundingBox()).width<=520);
    await page.locator('[data-close="detail-dialog"]').click();
    await newBrief();await assertCaptions(page,'brief editor');
    await page.locator('[data-close="brief-dialog"]').first().click();await page.locator('#nav-help').click();await assertCaptions(page,'help topics');
  });
  await scenario('touch captions without accidental searching',{touch:true,viewport:{width:320,height:900}},async({page,calls})=>{
    await page.locator('#query').fill('ovarian aging');
    const target=await page.locator('#search-button').boundingBox(),cdp=await page.context().newCDPSession(page);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:target.x+target.width/2,y:target.y+target.height/2}]});
    await page.locator('#control-caption').waitFor({state:'visible'});await assertCaptionFits(page);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});assert.equal(calls.queries.length,0);
    await page.locator('#search-button').tap();await page.waitForFunction(()=>state.search?.query==='ovarian aging');
    assert.equal(calls.queries.length,1);assert.equal(calls.guidance.length,0);await cdp.detach();
  });
  for(const width of [1365,390,320])await scenario('compact workspace '+width,{count:8,viewport:{width,height:950}},async({page,calls,search,newBrief})=>{
    for(const selector of ['#source-strip','aside.side','.search-options','.search-captions','.control-caption-guide'])assert.equal(await page.locator(selector).isVisible(),false);
    assert.equal(await page.locator('#workspace-title').textContent(),'Embryology research workspace');
    assert.equal(await page.locator('#query').inputValue(),'');
    assert.equal(await page.locator('#query').getAttribute('placeholder'),'e.g. Find research linking BRCA1 variants to breast cancer');
    assert.equal(await page.locator('#query').evaluate(n=>n.matches(':placeholder-shown')),true);
    assert.equal(await page.locator('#d-evidence').innerText(),'');
    assert.equal(await page.locator('#welcome').isVisible(),false);
    assert.equal(await page.locator('#search-page .intro').isVisible(),false);
    await page.screenshot({path:path.join(root,'test-results','empty-workspace-'+width+'.png'),fullPage:true});
    assert.equal(await page.locator('#app-version').textContent(),'V1.2.2');
    assert.equal(await page.locator('#search-page .intro h1').count(),0,'Workspace title is not duplicated');
    const header=await page.locator('.site-header').boundingBox(),legend=await page.locator('#content-provenance').boundingBox();
    assert.ok(legend.y>=header.y+header.height,'Legend directly follows the header');
    const help=await page.locator('#nav-help').boundingBox(),settings=await page.locator('#connection-button').boundingBox();
    assert.ok(help.x>=settings.x+settings.width);assert.equal(help.y,settings.y);
    await page.locator('#d-tab-sources').click();await page.locator('#d-content [data-source-id="gwas"]').waitFor();
    await page.getByLabel('Include GWAS Catalog in evidence searches',{exact:true}).uncheck();
    assert.equal(await page.evaluate(()=>selectedSources().includes('gwas')),false);
    await page.locator('#d-tab-evidence').click();
    await search('ovarian aging');assert.equal(calls.guidance.length,0,'Removed guidance panels do not spend AI tokens');
    assert.equal(await page.locator('#query').evaluate(n=>n.matches(':placeholder-shown')),false);
    assert.deepEqual(calls.queries,['ovarian aging'],'Typed searches contain only the user’s query');
    assert.equal(await page.locator('.record').count(),8);assert.equal(await page.locator('#results-heading').isVisible(),true);
    assert.equal(await page.locator('#recent').isVisible(),false);
    assert.deepEqual(await page.locator('.search-controls').getByRole('button').allTextContents(),['Overall Search']);
    assert.equal(await page.getByText('More actions',{exact:true}).count(),0);
    assert.equal(await page.getByText('Suggest research directions',{exact:true}).count(),0);
    await newBrief();
    await page.locator('#brief-title').fill('A manual brief');await page.locator('#brief-question').fill('What evidence is missing?');
    await page.locator('#brief-form button[type=submit]').click();
    assert.equal(calls.guidance.length,0,'Saving a brief does not trigger hidden guidance');
    await page.locator('.brand').click();await page.locator('#search-page').waitFor({state:'visible'});
    await page.screenshot({path:path.join(root,'test-results','workspace-'+width+'.png'),fullPage:true});
    if(width===1365){
      await page.getByRole('button',{name:'Inspect evidence',exact:true}).first().click();
      await page.getByRole('button',{name:'Explain with AI',exact:true}).click();await page.waitForFunction(()=>!state.aiController&&document.querySelector('#ai-output .ai-copy'));
      assert.ok(calls.actions.includes('explain'),'Explicit evidence explanations remain available');
      assert.equal(calls.queries.length,1);
    }
  });
  await scenario('saved research remains available from the workspace footer',{hosted:true,connected:false},async({page,calls})=>{
    await page.locator('#profile-settings').click();assert.equal(await page.locator('#nav-library').isDisabled(),true);
    await page.locator('#profile-dialog header button').click();await page.getByRole('button',{name:'Saved research',exact:true}).click();
    await page.locator('#saved-new').click();await page.locator('#brief-title').fill('Saved navigation check');await page.locator('#brief-question').fill('Can I reopen this brief from Settings?');
    await page.locator('#brief-form button[type=submit]').click();
    await page.locator('.brand').click();await page.getByRole('button',{name:'Saved research',exact:true}).click();
    assert.ok((await page.locator('#saved-list').innerText()).includes('Saved navigation check'));
    await page.reload();await page.locator('#search-page').waitFor({state:'visible'});assert.equal(await page.locator('#saved-page').isVisible(),false);
    assert.equal(calls.api.length,0,'Hosted mode makes no private backend or key requests');
  });
  await scenario('evidence colors and details remain readable',{mixed:true},async({page,search})=>{
    await search('ovarian aging');
    const colors=[];
    for(const source of ['pubmed','ensembl','gwas']){
      const card=page.locator('.record[data-source="'+source+'"]');assert.equal(await card.count(),1);
      colors.push(await card.locator('.tag[data-source]').evaluate(n=>getComputedStyle(n).backgroundImage));
    }
    assert.equal(new Set(colors).size,3);
    await page.locator('.record[data-source="pubmed"] h3 button').click();
    assert.equal(await page.locator('#detail-body .tag[data-source="pubmed"]').evaluate(n=>getComputedStyle(n).backgroundImage),colors[0]);
  });
  await scenario('missing key keeps evidence and manual work usable',{connected:false},async({page,calls,search})=>{
    await search('ovarian aging');assert.equal(calls.guidance.length,0);assert.equal(await page.locator('.record').count(),1);
    await page.getByRole('button',{name:'Inspect evidence',exact:true}).first().click();
    await page.getByRole('button',{name:'Explain with AI',exact:true}).click();await page.locator('#ai-setup-dialog').waitFor({state:'visible'});
    assert.equal(calls.actions.length,0);
  });
  await scenario('empty evidence never invokes AI',{empty:true},async({page,calls,search})=>{
    await search('ovarian aging');assert.equal(calls.actions.length,0);
    assert.deepEqual(await page.locator('.search-controls').getByRole('button').allTextContents(),['Overall Search']);
  });
  assert.deepEqual(pageErrors,[]);console.log(`${passed} browser scenarios passed; no page errors.`);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{await browser?.close();server.close();});
