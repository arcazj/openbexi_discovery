// Real profile revisions and storage, with synthetic remote APIs only.
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn,spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const {assertCaptions}=require('./caption_helpers.cjs');
const root=path.resolve(__dirname,'..'),temporary=fs.mkdtempSync(path.join(os.tmpdir(),'discovery-customization-ui-'));
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=process.env.TEST_PYTHON||(fs.existsSync(localPython)?localPython:'python');
const database=path.join(temporary,'sample.sqlite');
const prepared=spawnSync(python,['-c',"import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('CREATE TABLE sample (value INTEGER)'); c.execute('INSERT INTO sample VALUES (7)'); c.commit(); c.close()",database],{windowsHide:true});
assert.equal(prepared.status,0,String(prepared.stderr));
const base='http://127.0.0.1:18774';
const server=spawn(python,['-m','uvicorn','tests.data_ui_server:app','--host','127.0.0.1','--port','18774','--log-level','warning'],{
  cwd:root,windowsHide:true,env:{...process.env,DISCOVERY_DATA_DIR:temporary,DISCOVERY_LIBRARY_DIR:'',OPENAI_API_KEY:'sk-fixture-no-paid-calls',OPENAI_MODEL:'gpt-6-astra',OPENAI_REASONING_EFFORT:'xhigh'},stdio:['ignore','pipe','pipe']});
let logs='',browser;server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
async function api(route,body){const response=await fetch(base+'/api/discovery'+route,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.ok(response.ok,await response.clone().text());return response.json();}
async function ready(){for(let i=0;i<300;i++){if(server.exitCode!==null)throw new Error(logs);try{if((await fetch(base+'/api/health')).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}throw new Error('Server startup timed out');}
(async()=>{try{
  await ready();const original=(await api('/bootstrap')).profiles[0];
  const template=await api('/templates/general'),other=await api('/profiles/save',{profile:{...template,name:'Independent profile'},create:true});
  const note=await api('/library',{profile_id:'rei',kind:'note',title:'Preserve my research',content:'Saved before customization.'});
  browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1365,height:950}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.goto(base);await page.waitForFunction(()=>D.ready&&!D.connecting&&!!document.querySelector('#manage-themes'));
  const close=async id=>page.locator('#'+id+' header button').click();
  const remove=async id=>{const row=page.locator('#sources-dialog [data-source-id="'+id+'"]');await row.getByRole('button',{name:'Remove from workspace'}).click();await row.waitFor({state:'detached'});};
  await assertCaptions(page,'source bar management controls');
  fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  await page.screenshot({path:path.join(root,'test-results/source-management-desktop.png')});

  await page.locator('#manage-themes').click();await page.locator('#themes-dialog[open]').waitFor();const initialCount=await page.locator('#themes-dialog .d-chips button').count();
  await page.locator('#themes-dialog .d-chips button').first().click();assert.equal(await page.locator('#themes-dialog .d-chips button').count(),initialCount-1);
  await page.getByRole('button',{name:'Add theme',exact:true}).click();await page.getByLabel('Search research categories').fill('Quantum Physics');
  await page.locator('#themes-dialog .d-tree input[type=checkbox]').first().check();await assertCaptions(page,'direct theme catalogue');
  const chosen=await page.locator('#themes-dialog .d-tree input[type=checkbox]').first().evaluate(n=>n.closest('label').textContent.trim());
  const chosenId=await page.evaluate(name=>D.taxonomy.find(node=>node.name===name).id,chosen);
  await page.getByRole('button',{name:'Save themes',exact:true}).click();await page.locator('#themes-dialog').waitFor({state:'hidden'});
  assert.equal(await page.evaluate(()=>D.profile.id),'rei');assert.equal((await api('/bootstrap')).profiles.length,2,'Theme changes do not create extra profiles');
  const savedThemes=(await api('/bootstrap')).profiles.find(profile=>profile.id==='rei').themes;
  assert.deepEqual(savedThemes,[...original.themes.slice(1),chosenId],'All selected themes persist even when the compact title uses a more count');
  await page.locator('#manage-themes').click();assert.ok((await page.locator('#themes-dialog .d-chips').innerText()).includes(chosen));await close('themes-dialog');
  assert.deepEqual((await api('/library/'+note.id)).profile_snapshot.themes,original.themes,'Earlier material retains original themes');
  await page.locator('#source-update-notice').getByRole('button',{name:'Undo',exact:true}).click();
  await page.waitForFunction(themes=>JSON.stringify(D.profile.themes)===JSON.stringify(themes),original.themes);
  await page.locator('#manage-themes').click();await page.getByRole('button',{name:'Clear themes',exact:true}).click();await page.getByRole('button',{name:'Save themes',exact:true}).click();
  await page.locator('#themes-dialog').waitFor({state:'hidden'});assert.deepEqual(await page.evaluate(()=>D.profile.themes),[]);
  await page.locator('#source-update-notice').getByRole('button',{name:'Undo',exact:true}).click();
  await page.waitForFunction(themes=>JSON.stringify(D.profile.themes)===JSON.stringify(themes),original.themes);

  await page.locator('#manage-sources').click();await remove('gwas');await remove('pubmed');
  await page.locator('#sources-dialog').getByRole('button',{name:'Undo',exact:true}).click();await page.locator('#sources-dialog [data-source-id="pubmed"]').waitFor();
  await close('sources-dialog');assert.equal(await page.locator('[data-source="gwas"]').first().isVisible(),false);
  await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting&&!!document.querySelector('#manage-sources'));assert.equal(await page.locator('#source-gwas').isVisible(),false);
  assert.equal(await page.locator('#source-gwas').isChecked(),true,'Removing a source remembers its search checkbox preference');
  assert.ok(!(await page.evaluate(()=>selectedSources())).includes('gwas'),'Hidden sources cannot participate in a search');
  await page.locator('#profile-settings').click();await page.locator('#profile-dialog .d-row').filter({has:page.getByRole('heading',{name:'Independent profile',exact:true})}).getByRole('button',{name:'Use profile'}).click();
  await page.locator('#profile-dialog').waitFor({state:'hidden'});await page.waitForFunction(id=>D.profile.id===id,other.id);assert.equal(await page.locator('#source-gwas').isVisible(),true,'Other profiles keep their own source list');
  await page.locator('#profile-settings').click();await page.locator('#profile-dialog .d-row').filter({has:page.getByRole('heading',{name:'REI',exact:true})}).getByRole('button',{name:'Use profile'}).click();
  await page.locator('#profile-dialog').waitFor({state:'hidden'});await page.waitForFunction(()=>D.profile.id==='rei');assert.equal(await page.locator('#source-gwas').isVisible(),false);
  await page.locator('#add-source').click();await page.locator('#add-source-dialog [data-source-id="gwas"]').getByRole('button',{name:'Add to workspace'}).click();
  await page.waitForFunction(()=>!D.profile.hidden_source_ids.includes('gwas'));await assertCaptions(page,'Add source catalogue');
  await page.getByRole('button',{name:'Use Crossref',exact:true}).click();await page.locator('#api-connect-dialog[open]').waitFor();
  assert.equal(await page.getByLabel('API URL',{exact:true}).inputValue(),'https://api.crossref.org/works');
  await page.getByRole('button',{name:'Test & save connection'}).click();await page.locator('#api-explorer-dialog[open]').waitFor();await close('api-explorer-dialog');
  const connection=(await api('/api-connections?profile_id=rei')).connections[0];
  await page.locator('#connected-source-shortcuts [data-source-id="api:'+connection.id+'"]').click();await page.locator('#api-explorer-dialog[open]').waitFor();await close('api-explorer-dialog');
  await page.locator('#add-source').click();await page.locator('#add-source-dialog').getByRole('button',{name:'Connect SQLite database'}).click();
  await page.locator('#connect-dialog').getByLabel('Connection name',{exact:true}).fill('Local study');await page.getByLabel('Existing database path on this computer (optional)').fill(database);
  await page.getByRole('button',{name:'Connect read-only'}).click();await page.locator('#connect-dialog').waitFor({state:'hidden'});
  const sqlite=(await api('/connections?profile_id=rei')).connections[0];
  await page.locator('#connected-source-shortcuts [data-source-id="sqlite:'+sqlite.id+'"]').click();await page.locator('#database-dialog[open]').waitFor();await close('database-dialog');
  await page.locator('#manage-sources').click();await remove('api:'+connection.id);await remove('sqlite:'+sqlite.id);await assertCaptions(page,'source removal');await close('sources-dialog');
  assert.equal((await api('/api-connections?profile_id=rei')).connections.length,1,'Removing a workspace source preserves its saved API connection');
  assert.equal((await api('/connections?profile_id=rei')).connections.length,1,'Removing a workspace source preserves its saved database connection');
  assert.equal(await page.locator('#connected-source-shortcuts').isVisible(),false);
  await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting&&!!document.querySelector('#manage-sources'));await page.locator('#add-source').click();
  await page.locator('#add-source-dialog [data-source-id="api:'+connection.id+'"]').getByRole('button',{name:'Add to workspace'}).click();
  await page.locator('#add-source-dialog [data-source-id="sqlite:'+sqlite.id+'"]').getByRole('button',{name:'Add to workspace'}).click();await close('add-source-dialog');
  await page.locator('#connected-source-shortcuts [data-source-id="sqlite:'+sqlite.id+'"]').waitFor();
  assert.equal((await api('/library/'+note.id)).content,note.content);
  await page.locator('#manage-sources').click();for(const id of ['pubmed','ensembl','gwas'])await remove(id);await close('sources-dialog');
  assert.equal(await page.locator('#empty-source-selection').isVisible(),true);assert.deepEqual(await page.evaluate(()=>selectedSources()),[]);
  await page.locator('#recommended').click();await page.waitForFunction(()=>selectedSources().length===3);assert.equal(await page.locator('#empty-source-selection').isVisible(),false);

  for(const width of [390,320]){
    await page.setViewportSize({width,height:950});await page.evaluate(()=>scrollTo(0,0));
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Source bar fits at '+width);
    await page.screenshot({path:path.join(root,'test-results/source-management-mobile-'+width+'.png'),fullPage:true});
    await page.locator('#manage-themes').click();await page.getByRole('button',{name:'Add theme',exact:true}).click();
    assert.equal(await page.locator('#themes-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Theme catalogue fits at '+width);await close('themes-dialog');
    await page.locator('#add-source').click();await page.getByRole('heading',{name:'Crossref',exact:true}).waitFor();
    assert.equal(await page.locator('#add-source-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Source catalogue fits at '+width);
    await page.screenshot({path:path.join(root,'test-results/source-catalogue-mobile-'+width+'.png')});await close('add-source-dialog');
  }
  await page.setViewportSize({width:320,height:640});
  await page.locator('#d-tab-quizzes').click();await page.getByRole('button',{name:'Start a quiz',exact:true}).waitFor();
  assert.equal(await page.locator('#source-strip').evaluate(n=>getComputedStyle(n).position),'static','Short screens can scroll past the expanded source bar');
  assert.deepEqual(errors,[]);console.log('PASS Theme add/remove/undo, profile isolation, source catalogue, API/SQLite shortcuts, durable source removal/restoration, preserved research, and mobile layout.');
}finally{
  if(browser)await browser.close();server.kill();await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));
  assert.equal(path.dirname(path.resolve(temporary)),path.resolve(os.tmpdir()));assert.ok(path.basename(temporary).startsWith('discovery-customization-ui-'));
  fs.rmSync(temporary,{recursive:true,force:true});
}})().catch(error=>{console.error(error);console.error(logs.slice(-2500));process.exitCode=1;});
