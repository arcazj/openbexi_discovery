// Real profile proposals, revisions and rollback; synthetic AI and search responses.
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require('playwright');
const {assertCaptions}=require('./caption_helpers.cjs');
const root=path.resolve(__dirname,'..'),temporary=fs.mkdtempSync(path.join(os.tmpdir(),'discovery-profile-ai-ui-'));
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=process.env.TEST_PYTHON||(fs.existsSync(localPython)?localPython:'python'),base='http://127.0.0.1:18775';
const server=spawn(python,['-m','uvicorn','tests.data_ui_server:app','--host','127.0.0.1','--port','18775','--log-level','warning'],{
  cwd:root,windowsHide:true,env:{...process.env,DISCOVERY_DATA_DIR:temporary,DISCOVERY_LIBRARY_DIR:'',OPENAI_API_KEY:'sk-fixture-no-paid-calls',OPENAI_MODEL:'gpt-6-astra',OPENAI_REASONING_EFFORT:'xhigh'},stdio:['ignore','pipe','pipe']});
let logs='',browser,holdNextDraft=false,pendingDrafts=[];server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
async function api(route,body){const response=await fetch(base+'/api/discovery'+route,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.ok(response.ok,await response.clone().text());return response.json();}
async function ready(){for(let i=0;i<300;i++){if(server.exitCode!==null)throw new Error(logs);try{if((await fetch(base+'/api/health')).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}throw new Error('Server startup timed out');}
(async()=>{try{
  await ready();const original=(await api('/bootstrap')).profiles[0];
  const other=await api('/profiles/save',{profile:{...await api('/templates/general'),name:'Physics',themes:['02.01'],theme_title:'Physics',goal:'Explore quantum physics.'},create:true});
  const note=await api('/library',{profile_id:'rei',kind:'note',title:'Keep my note',content:'Saved before updating the profile.'});
  browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1365,height:950}}),errors=[],drafts=[];
  await page.clock.install();
  page.on('pageerror',e=>{errors.push(e.message);console.error('Page error:',e.message);});page.on('dialog',d=>d.accept());
  await page.addInitScript(()=>localStorage.setItem('rei-research-preferences-v1',JSON.stringify({autoGuidance:false})));
  let quota=false;
  await page.route('**/api/discovery/ai/draft',async route=>{
    drafts.push(route.request().postDataJSON());
    if(quota)return route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:{code:'insufficient_quota',message:'AI tokens are unavailable. Add credits, then retry.'}})});
    if(holdNextDraft){holdNextDraft=false;const response=await route.fetch();await new Promise(resolve=>pendingDrafts.push(resolve));return route.fulfill({response}).catch(()=>{});}
    return route.continue();
  });
  await page.route('**/api/search',async route=>{
    const {query}=route.request().postDataJSON();
    if(query==='PCOS unavailable')return route.fulfill({status:503,body:JSON.stringify({detail:'Synthetic search failure'})});
    if(query==='PCOS slow')await new Promise(r=>setTimeout(r,600));
    const record={id:'pubmed:123456',source:'pubmed',type:'publication',title:'Synthetic search result',summary:'Fixture evidence.',url:'https://pubmed.ncbi.nlm.nih.gov/123456/',metadata:{abstract_available:true},authors:[]};
    return route.fulfill({contentType:'application/json',body:JSON.stringify({query,records:[record],coverage:[{source:'pubmed',status:'ok',total:1,retrieved:1,truncated:false,query}],retrieved_at:new Date().toISOString(),demo:false})}).catch(()=>{});
  });
  await page.goto(base);await page.waitForFunction(()=>D.ready&&!D.connecting).catch(async error=>{console.error(await page.evaluate(()=>({ready:D.ready,health:state.health,toast:$('toast')?.textContent,body:document.body.innerText.slice(-1500)})));throw error;});
  const close=async id=>page.locator('#'+id+' header button').click();
  const settings=async()=>{await page.locator('#profile-settings').click();await page.locator('#profile-dialog[open]').waitFor();};
  const generate=async()=>{await page.locator('#profile-update-generate').click();await page.locator('#profile-update-apply').waitFor();};
  const search=async query=>{
    await page.locator('#query').fill(query);
    const saved=page.waitForResponse(r=>r.url().endsWith('/api/discovery/library')&&r.request().method()==='POST');
    await page.locator('#search-button').click();await saved;
    await page.waitForFunction(()=>!state.searchController);
  };
  assert.equal(await page.locator('#profile-search-update').isVisible(),false);
  await search('ovarian aging');await page.locator('#profile-search-update').waitFor();
  assert.equal(drafts.length,0,'Related search does not make a profile AI call');
  assert.equal((await api('/bootstrap')).profiles.find(p=>p.id==='rei').revision,1);
  await page.locator('#profile-search-update').click();await page.locator('#profile-update-dialog[open]').waitFor();
  assert.ok((await page.locator('#profile-update-request').inputValue()).includes('ovarian aging'));
  assert.equal(drafts.length,0,'Opening the shortcut does not make an AI call');
  assert.equal(await page.locator('#profile-update-level').isChecked(),false);
  assert.equal(await page.locator('#profile-update-layout').isChecked(),false);
  await assertCaptions(page,'search-based profile update');
  holdNextDraft=true;await page.locator('#profile-update-generate').click();
  await page.locator('#profile-update-working').waitFor();
  assert.equal(await page.locator('#profile-update-generate').isDisabled(),true);
  assert.equal(await page.locator('#profile-update-preview').getAttribute('aria-busy'),'true');
  assert.equal(await page.getByRole('progressbar',{name:'Preparing profile preview'}).getAttribute('aria-valuenow'),null,'Indeterminate progress does not claim a fabricated percentage');
  await page.clock.fastForward(46000);
  await page.getByText('AI is still working. Thank you for your patience.',{exact:true}).waitFor();
  await assertCaptions(page,'AI preparation and cancellation');
  fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  await page.screenshot({path:path.join(root,'test-results/profile-preparing-desktop.png')});
  await page.setViewportSize({width:320,height:740});await page.locator('#ai-work-status').scrollIntoViewIfNeeded();
  assert.equal(await page.locator('#profile-update-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false);
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await page.locator('.d-ai-progress span').evaluate(n=>getComputedStyle(n).animationName),'none');
  await page.screenshot({path:path.join(root,'test-results/profile-preparing-mobile.png')});
  await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1365,height:950});
  pendingDrafts.splice(0).forEach(resolve=>resolve());await page.locator('#profile-update-apply').waitFor();
  assert.equal(await page.locator('#profile-update-working').isVisible(),false);
  assert.equal(await page.locator('#profile-update-preview').getAttribute('aria-busy'),'false');
  assert.equal((await api('/bootstrap')).profiles.find(p=>p.id==='rei').revision,1,'Generating a preview does not save');
  assert.equal(drafts[0].allow_level_change,false);assert.equal(drafts[0].allow_layout_changes,false);
  await assertCaptions(page,'profile change review');
  fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  await page.screenshot({path:path.join(root,'test-results/profile-update-preview-desktop.png')});
  await page.getByLabel('Apply Search examples',{exact:true}).uncheck();
  await page.getByLabel('Apply Tip text',{exact:true}).uncheck();
  await page.locator('#profile-update-apply').click();await page.locator('#profile-update-dialog').waitFor({state:'hidden'});
  let saved=await page.evaluate(()=>D.profile);
  assert.equal(saved.revision,2);assert.notEqual(saved.goal,original.goal);assert.deepEqual(saved.ui,original.ui);
  assert.deepEqual(saved.tabs,original.tabs);assert.equal(saved.learning_level,original.learning_level);
  await page.locator('#source-update-notice').getByRole('button',{name:'Roll back profile',exact:true}).click();
  await page.waitForFunction(goal=>D.profile.goal===goal,original.goal);
  assert.deepEqual((await api('/library/'+note.id)).profile_snapshot.goal,original.goal);

  await settings();await page.locator('#profile-update-request').fill('Focus on ovarian aging. Change my level to researcher and simplify the tabs.');
  await page.locator('#profile-update-level').check();await page.locator('#profile-update-layout').check();await generate();
  assert.equal(await page.getByLabel('Apply Learning level',{exact:true}).isChecked(),false);
  assert.equal(await page.getByLabel('Apply Workspace layout (tabs and side panels)',{exact:true}).isChecked(),false);
  await page.getByLabel('Apply Learning level',{exact:true}).check();await page.getByLabel('Apply Workspace layout (tabs and side panels)',{exact:true}).check();
  await page.locator('#profile-update-apply').click();await page.locator('#profile-dialog').waitFor({state:'hidden'});
  assert.equal(await page.evaluate(()=>D.profile.learning_level),'researcher');
  assert.equal(await page.locator('[role=tab]').count(),3);
  await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting);
  await settings();await page.locator('[data-profile-id="rei"]').getByRole('button',{name:'Roll back profile',exact:true}).click();
  await page.waitForFunction(()=>D.profile.learning_level==='advanced');
  assert.deepEqual(await page.evaluate(()=>D.profile.ui),original.ui);
  assert.equal(await page.locator('[role=tab]').count(),6);await close('profile-dialog');

  await search('quantum entanglement');await page.waitForFunction(()=>$('profile-search-tip').hidden);
  await search('PCOS');await page.locator('#profile-search-update').waitFor();
  await page.locator('#query').fill('PCOS unavailable');await page.locator('#search-button').click();
  await page.getByRole('heading',{name:'Search unavailable',exact:true}).waitFor();assert.equal(await page.locator('#profile-search-update').isVisible(),false);
  const beforeCancel=(await api('/library?profile=rei&kind=search')).activities.length;
  await page.locator('#query').fill('PCOS slow');await page.locator('#search-button').click();await page.locator('#cancel-search').click();
  await page.waitForFunction(()=>!state.searchController);assert.equal((await api('/library?profile=rei&kind=search')).activities.length,beforeCancel);

  await settings();await page.locator('[data-profile-id="'+other.id+'"]').getByRole('button',{name:'Use profile',exact:true}).click();
  await page.waitForFunction(id=>D.profile.id===id,other.id);assert.equal(await page.locator('#profile-search-update').isVisible(),false);
  await settings();assert.ok((await page.locator('.d-profile-update').innerText()).includes('Physics'));
  await page.locator('[data-profile-id="rei"]').getByRole('button',{name:'Use profile',exact:true}).click();await page.waitForFunction(()=>D.profile.id==='rei'&&!D.suppressSave);

  await settings();await page.locator('#profile-update-request').fill('Focus my goal on ovarian aging.');await generate();
  await page.locator('#profile-update-request').fill('Keep a different research goal.');assert.equal(await page.locator('#profile-update-apply').isVisible(),false,'Editing instructions invalidates an earlier preview');
  await page.locator('#profile-update-sensitive').check();const beforeSensitive=drafts.length;
  await page.locator('#profile-update-generate').click();await page.locator('#sensitive-dialog[open]').waitFor();
  await page.locator('#sensitive-dialog').getByRole('button',{name:'Cancel',exact:true}).click();assert.equal(drafts.length,beforeSensitive);
  await page.locator('#profile-update-generate').click();await page.locator('#sensitive-dialog').getByRole('button',{name:'Send this request',exact:true}).click();
  await page.locator('#profile-update-apply').waitFor();assert.equal(drafts.at(-1).consent_ai,true);
  const activities=(await api('/library?profile=rei&kind=ai')).activities,latest=await api('/library/'+activities[0].id);
  assert.equal(latest.request,'[sensitive request omitted]');assert.deepEqual(latest.prompts,[]);
  await page.getByRole('button',{name:'Discard preview',exact:true}).click();
  await page.locator('#profile-update-sensitive').uncheck();await generate();
  const external=(await api('/bootstrap')).profiles.find(p=>p.id==='rei');
  await api('/profiles/save',{profile:{...external,goal:'Edited in another window'},base_revision:external.revision});
  await page.locator('#profile-update-apply').click();await page.getByText('This profile changed. Reload it before saving.',{exact:true}).waitFor();
  assert.equal((await api('/bootstrap')).profiles.find(p=>p.id==='rei').goal,'Edited in another window');
  await close('profile-dialog');await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting);

  await settings();await page.locator('#profile-update-request').fill('Focus my research on ovarian aging.');await generate();
  for(const width of [390,320]){
    await page.setViewportSize({width,height:740});await assertCaptions(page,'mobile profile preview '+width);
    await page.locator('#profile-update-preview').evaluate(node=>node.scrollIntoView({block:'start'}));
    assert.equal(await page.locator('#profile-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false);
    await page.screenshot({path:path.join(root,'test-results/profile-update-preview-mobile-'+width+'.png')});
  }
  await page.getByRole('button',{name:'Discard preview',exact:true}).click();quota=true;
  await page.locator('#profile-update-generate').click();await page.locator('.d-profile-update .d-status').filter({hasText:'AI tokens are unavailable'}).waitFor();
  assert.equal(await page.locator('#profile-update-apply').isVisible(),false);
  assert.equal(await page.locator('#profile-update-working').isVisible(),false,'A failed request clears the busy indicator');
  quota=false;await page.setViewportSize({width:1365,height:950});
  const beforeCancelProfile=await page.evaluate(()=>D.profile);
  holdNextDraft=true;await page.locator('#profile-update-generate').click();await page.locator('#profile-update-working').waitFor();
  await page.locator('#profile-update-cancel').click();
  await page.getByText('Preparation canceled. Your profile has not changed.',{exact:true}).waitFor();
  assert.equal(await page.locator('#profile-update-working').isVisible(),false);
  pendingDrafts.splice(0).forEach(resolve=>resolve());
  await page.waitForFunction(()=>!$('profile-update-generate').disabled);
  assert.equal(await page.locator('#profile-update-apply').isVisible(),false);
  assert.deepEqual(await page.evaluate(()=>D.profile),beforeCancelProfile);
  await generate();await page.locator('#profile-update-apply').click();await page.locator('#profile-dialog').waitFor({state:'hidden'});
  await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting);await settings();
  const appliedRevision=await page.evaluate(()=>D.profile.revision),usage=(await api('/budget')).total_tokens;
  await page.locator('#profile-update-request').fill('Please focus my research on ovarian aging!');
  await page.evaluate(()=>{state.aiQuotaError='AI tokens unavailable in fixture';renderAIAvailability();});
  await page.locator('#profile-update-generate').click();await page.locator('#profile-update-preview').getByRole('heading',{name:'No profile changes needed',exact:true}).waitFor();
  assert.ok((await page.locator('#profile-update-preview').innerText()).includes('You already requested this update'));
  assert.ok((await page.locator('#profile-update-preview').innerText()).includes('no AI request made'));
  assert.equal((await api('/budget')).total_tokens,usage);
  assert.equal(await page.evaluate(()=>D.profile.revision),appliedRevision);
  assert.equal(await page.evaluate(()=>state.aiQuotaError),'AI tokens unavailable in fixture','Cached repeat does not falsely claim quota recovered');
  assert.equal(await page.locator('#profile-update-apply').count(),0);
  await page.locator('#profile-update-request').fill('Tailor my workspace around fertility outcomes and ovarian ageing.');
  await page.locator('#profile-update-generate').click();await page.locator('#profile-update-preview').getByRole('heading',{name:'No profile changes needed',exact:true}).waitFor();
  assert.ok((await page.locator('#profile-update-preview').innerText()).includes('same research focus'));
  assert.equal(await page.evaluate(()=>D.profile.revision),appliedRevision);
  await close('profile-dialog');
  // Keep model attribution on the requested plain-background sections.
  await page.evaluate(()=>{
    const provenance={origin:'ai',model:'fixture-model',generated_at:new Date().toISOString()};
    for(const key of ['eyebrow','heading','introduction','sources_title','sources_caption','search_placeholder','search_label','examples','theme_title','goal','tip_text'])D.profile.provenance[key]=provenance;
    D.profile.ui.eyebrow='Embryology research workspace';D.profile.ui.introduction='Study embryo development and compare outcomes.';
    state.search=null;applyProfile();updateGuidance();
  });
  const colors=await page.evaluate(()=>{
    const aiColor=getComputedStyle(document.querySelector('#content-provenance .d-ai')).backgroundColor;
    const selectors=['.intro h1','.intro p span','#source-list-label','.source-caption','#d-theme small','#query','.examples'];
    return {aiColor,plain:selectors.map(selector=>{const node=document.querySelector(selector);return {selector,color:getComputedStyle(node).backgroundColor,origin:node.dataset.provenance};}),tip:getComputedStyle($('guidance-tip')).backgroundColor};
  });
  for(const item of colors.plain){assert.equal(item.origin,'ai');assert.notEqual(item.color,colors.aiColor,item.selector+' keeps its standard background');}
  assert.equal(colors.tip,colors.aiColor,'AI content outside the exception remains orange');
  await page.screenshot({path:path.join(root,'test-results/profile-plain-heading-controls.png')});
  assert.deepEqual(errors,[]);
  console.log('PASS Profile updates and rollback; progress, elapsed time, cancellation and reduced motion; repeated/similar requests without profile changes; quota preservation; plain heading/source/search controls with attribution; mobile captions.');
}finally{
  pendingDrafts.splice(0).forEach(resolve=>resolve());
  if(browser)await browser.close();server.kill();await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));
  assert.equal(path.dirname(path.resolve(temporary)),path.resolve(os.tmpdir()));assert.ok(path.basename(temporary).startsWith('discovery-profile-ai-ui-'));
  fs.rmSync(temporary,{recursive:true,force:true});
}})().catch(error=>{console.error(error);console.error(logs.slice(-2500));process.exitCode=1;});
