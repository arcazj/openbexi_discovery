const {assertCaptions} = require('./caption_helpers.cjs');
// Exercise real Python persistence and the new UI, without a key or paid calls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const {spawn,spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=process.env.TEST_PYTHON||(fs.existsSync(localPython)?localPython:'python');
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'discovery-ui-'));
const port=18772;
const base='http://127.0.0.1:'+port;
const database=path.join(temporary,'fixture.sqlite');
const made=spawnSync(python,['-c',"import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('CREATE TABLE research (participant TEXT, gene TEXT, outcome REAL)'); c.execute(\"INSERT INTO research VALUES ('P01','BRCA1',1.0)\"); c.commit(); c.close()",database],{cwd:root,windowsHide:true});
assert.equal(made.status,0,made.stderr?.toString());
const server=spawn(python,['serve_frontend.py','--port',String(port),'--strict-port'],{cwd:root,windowsHide:true,env:{...process.env,OPENAI_API_KEY:'',OPENAI_MODEL:'',OPENAI_REASONING_EFFORT:'',DISCOVERY_DATA_DIR:temporary,DISCOVERY_LIBRARY_DIR:''},stdio:['ignore','pipe','pipe']});
let logs='';server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
let browser;
async function waitServer(){for(let i=0;i<450;i++){if(server.exitCode!==null)throw new Error(logs);try{if((await fetch(base+'/api/health')).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}throw new Error('Backend did not start: '+logs);}
async function api(route,body){const r=await fetch(base+'/api/discovery'+route,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.ok(r.ok,await r.clone().text());return r.json();}
(async()=>{try{await waitServer();browser=await chromium.launch({headless:true});const errors=[];const page=await browser.newPage({viewport:{width:1365,height:950}});await page.route('**/api/search',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({query:route.request().postDataJSON().query,records:[],coverage:[],retrieved_at:new Date().toISOString()})}));page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());let backendAvailable=false;await page.route('**/api/health',route=>backendAvailable?route.continue():route.fulfill({status:503,body:'Backend starting'}));await page.goto(base);await page.waitForTimeout(5500);assert.equal(await page.evaluate(()=>D.ready),false);backendAvailable=true;await page.locator('#profile-settings').click();await page.locator('#profile-dialog[open]').waitFor();await page.waitForFunction(()=>D.ready&&D.profile?.id==='rei');await page.locator('#profile-dialog header button').click();
  await page.locator('#profile-settings').click();await page.locator('#profile-dialog[open]').waitFor();const settingsText=await page.locator('#profile-dialog').innerText();await assertCaptions(page,'profile settings');await page.locator('#profile-dialog header button').click();
  await page.locator('#profile-settings').click();await page.locator('#profile-dialog[open]').waitFor();assert.equal(await page.locator('#profile-dialog').innerText(),settingsText,'Settings remains consistent when reopened');assert.equal(await page.getByLabel('Profile name',{exact:true}).count(),0,'Opening Settings does not start profile creation');await page.locator('#profile-dialog header button').click();
  for(const id of ['connection-button','profile-settings'])assert.ok((await page.locator('#'+id).boundingBox()).height>=44,'Settings click target at least 44px');
  assert.equal(await page.locator('#app-version').textContent(),'V1.2.2');assert.equal(await page.locator('[role=tab]').count(),7);
  await page.waitForFunction(()=>!state.searchController&&state.search?.query===DEFAULT_QUERY);assert.equal(await page.locator('#results-heading').isVisible(),true,'Default evidence search runs on launch');
  const legacy=await page.evaluate(()=>{const p=clone(D.profile);p.ui.eyebrow='Your fellowship research workspace';p.ui.heading='Find evidence. Shape a question.';p.ui.introduction='Explore a topic, gene, or genomic region. Keep the evidence and the next question together.';alignProfileWording(p);return p.ui;});
  assert.equal(legacy.heading,'');assert.equal(legacy.introduction,'Explore topics, genes, or genomic regions to find evidence and shape your next question.');
  await page.route('**/api/ai/check',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({accessible:true,message:'Synthetic model access; no provider call.'})}));
  await page.getByRole('button',{name:/^Connect AI/}).click();
  await page.getByRole('heading',{name:'By profile and model',exact:true}).waitFor();
  assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'gpt-6-astra');
  assert.equal(await page.getByLabel('Reasoning',{exact:true}).inputValue(),'xhigh');
  assert.equal(await page.getByText('Usage & budget',{exact:true}).count(),0);
  assert.equal(await page.locator('#ai-connect-action').count(),0,'One AI connection button replaces redundant settings');
  assert.equal(await page.getByLabel('Enable Token limit',{exact:true}).count(),0);
  await page.screenshot({path:path.join(root,'test-results/ai-settings-desktop.png'),fullPage:true});
  for(const width of [390,320]){
    await page.setViewportSize({width,height:900});
    assert.equal(await page.locator('#ai-setup-dialog').evaluate(node=>node.scrollWidth>node.clientWidth),false,'AI settings fit at '+width);
    await page.screenshot({path:path.join(root,'test-results/ai-settings-mobile-'+width+'.png'),fullPage:true});
  }
  await page.setViewportSize({width:1365,height:950});
  await page.getByLabel('Model',{exact:true}).selectOption('gpt-6.1-sol');await page.getByLabel('Reasoning',{exact:true}).selectOption('low');
  await page.getByLabel('OpenAI API key',{exact:true}).fill('sk-browser-fixture-not-a-real-key');await page.getByRole('button',{name:'Save & connect',exact:true}).click();
  await page.waitForSelector('#ai-setup-dialog:not([open])',{state:'attached'});
  await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting&&state.aiStatus?.phase==='ready');
  await page.locator('#connection-button').click();
  assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'gpt-6.1-sol');assert.equal(await page.getByLabel('Reasoning',{exact:true}).inputValue(),'low');
  assert.equal(await page.getByLabel('OpenAI API key',{exact:true}).inputValue(),'');
  await page.getByLabel('Model',{exact:true}).selectOption('gpt-6-astra');await page.getByLabel('Reasoning',{exact:true}).selectOption('xhigh');
  await page.getByRole('button',{name:'Save & connect',exact:true}).click();await page.waitForSelector('#ai-setup-dialog:not([open])',{state:'attached'});
  assert.match(await page.locator('#connection-label').textContent(),/GPT-6 Astra.*xHigh/);
  await page.route('**/api/discovery/ai/draft',async route=>{if(route.request().postDataJSON().task!=='generate_profile')return route.continue();const profile=await api('/templates/cosmologie');profile.name='Physics explorer';return route.fulfill({contentType:'application/json',body:JSON.stringify({decision:'accepted',profile})});});
  await page.locator('#profile-settings').click();await page.getByRole('button',{name:'Create new profile',exact:true}).click();await page.getByLabel('Field or area of interest',{exact:true}).fill('Physics exploration');await page.getByRole('button',{name:'Create new profile',exact:true}).click();await page.waitForFunction(()=>D.profile?.name==='Physics explorer'&&!document.querySelector('#profile-dialog').open);await page.locator('#profile-settings').click();await page.getByText('Profile options',{exact:true}).click();await page.getByRole('button',{name:'Edit profile',exact:true}).click();await page.getByLabel('Learning or research goal',{exact:true}).fill('Understand physical ideas through evidence and practice.');await page.getByLabel('Theme summary',{exact:true}).fill('Physics learning');await page.getByText('Browse theme catalogue',{exact:true}).click();await page.getByLabel('Search research categories').fill('Quantum Physics');await page.locator('.d-tree input[type=checkbox]').first().check();await page.getByText('Edit page wording',{exact:true}).click();
  await page.getByLabel('Workspace heading',{exact:true}).fill('My physics workspace');await page.getByLabel('Description lead-in (optional)',{exact:true}).fill('Explore physics.');await page.getByLabel('Workspace description',{exact:true}).fill('Connect evidence and ideas.');
  assert.equal(await page.getByLabel('welcome heading',{exact:true}).count(),0,'Removed heading is absent from profile controls');
  await assertCaptions(page,'profile editor and taxonomy');await page.getByRole('button',{name:'Preview',exact:true}).click();
  assert.equal(await page.locator('.d-preview .intro h1').textContent(),'My physics workspace');
  assert.equal(await page.locator('.d-preview .intro p').textContent(),'Explore physics. Connect evidence and ideas.');
  assert.equal(await page.locator('.d-preview .intro p').evaluate(n=>getComputedStyle(n).fontSize),'12px');
  await page.getByRole('button',{name:'Save profile',exact:true}).click();await page.waitForFunction(()=>D.profile?.name==='Physics explorer'&&!document.querySelector('#profile-dialog').open);const pid=await page.evaluate(()=>D.profile.id);assert.notEqual(pid,'rei');assert.equal(await page.locator('#workspace-title').textContent(),'My physics workspace');assert.equal(await page.locator('#search-page .intro p').textContent(),'Explore physics. Connect evidence and ideas.');
  await page.locator('#d-tab-notes').click();await page.getByRole('button',{name:'New note',exact:true}).click();await page.getByLabel('Title',{exact:true}).fill('Evidence notebook');await page.getByLabel('Content / notes').fill('A saved note with <script>unsafe()</script> shown as text.');await page.getByRole('button',{name:'Save locally',exact:true}).click();await page.waitForSelector('#material-dialog:not([open])',{state:'attached'});await page.locator('#d-tab-evidence').click();await page.locator('#d-tab-notes').click();await page.getByRole('button',{name:'Refresh',exact:true}).click();assert.ok((await page.locator('#d-content').innerText()).includes('Evidence notebook'));
  await page.locator('#d-tab-quizzes').click();await page.getByRole('button',{name:'Create quiz',exact:true}).click();await page.getByLabel('Title',{exact:true}).fill('Evidence quiz');await page.getByRole('button',{name:'Save locally',exact:true}).click();await page.waitForSelector('#material-dialog:not([open])',{state:'attached'});await page.getByRole('button',{name:'Refresh',exact:true}).click();await page.locator('#d-content').getByRole('button',{name:'Start',exact:true}).first().click();await page.getByRole('radio',{name:'A traceable source'}).check();await page.getByRole('button',{name:'Grade & save attempt'}).click();await page.getByRole('heading',{name:'Score: 1 / 1'}).waitFor();await page.locator('#activity-dialog header button').click();
  // Synthetic AI, real quiz persistence and grading. No provider request is made.
  const quizDrafts=[];let holdQuiz=true,releaseQuiz;
  await page.route('**/api/discovery/ai/draft',async route=>{
    const request=route.request().postDataJSON();quizDrafts.push(request);
    assert.equal(request.task,'create_quiz');
    if(holdQuiz){holdQuiz=false;await new Promise(resolve=>releaseQuiz=resolve);}
    await route.fulfill({contentType:'application/json',body:JSON.stringify({title:'Physics practice',
      questions:Array.from({length:8},(_,i)=>({question:'Evidence question '+(i+1),choices:['Choice A','Choice B','Choice C','Choice D'],answer:i%4,explanation:'Explanation for question '+(i+1)})),
      provenance:{origin:'ai',model:'gpt-6-astra',generated_at:'2026-10-11T12:00:00Z'},reasoning_effort:'xhigh'})}).catch(()=>{});
  });
  await page.getByRole('button',{name:'Start a quiz',exact:true}).click();
  await page.locator('#quiz-start-dialog').getByRole('progressbar',{name:'Creating an 8-question quiz',exact:true}).waitFor();
  await assertCaptions(page,'quiz generation progress');
  assert.ok((await page.locator('#ai-work-status').innerText()).includes('Please wait'));
  await page.screenshot({path:path.join(root,'test-results/quiz-progress-desktop.png')});
  for(const width of [390,320]){
    await page.setViewportSize({width,height:740});
    assert.equal(await page.locator('#quiz-start-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false);
    const box=await page.locator('#ai-work-status').boundingBox();assert.ok(box&&box.y>=0&&box.y+box.height<=740,'Quiz progress remains visible on mobile');
    await page.screenshot({path:path.join(root,'test-results/quiz-progress-mobile-'+width+'.png')});
  }
  await page.locator('#quiz-start-dialog').getByRole('button',{name:'Cancel',exact:true}).click();
  await page.locator('#ai-work-status').waitFor({state:'detached'});releaseQuiz();
  assert.equal((await api('/library?profile='+pid+'&kind=quiz')).activities.length,1,'Canceling preparation does not save a generated quiz');
  await page.setViewportSize({width:1365,height:950});
  await page.getByRole('button',{name:'Start a quiz',exact:true}).click();
  await page.locator('#activity-dialog').getByRole('heading',{name:'Physics practice',exact:true}).waitFor();
  assert.equal(quizDrafts.length,2);assert.equal(quizDrafts[0].profile.id,pid);
  assert.equal(quizDrafts[0].profile.learning_level,await page.evaluate(()=>D.profile.learning_level));
  await assertCaptions(page,'eight-question quiz');assert.equal(await page.locator('.d-quiz-question').count(),8);
  assert.equal(await page.locator('.d-quiz-question.d-ai').count(),8);
  await page.getByRole('button',{name:'Grade & save attempt'}).click();
  assert.equal((await api('/quiz/history?profile_id='+pid)).attempts.length,1,'Incomplete answers do not save an attempt');
  await page.screenshot({path:path.join(root,'test-results/quiz-desktop.png'),fullPage:true});
  for(const width of [390,320]){
    await page.setViewportSize({width,height:900});
    assert.equal(await page.locator('#activity-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Quiz fits at '+width);
    await page.screenshot({path:path.join(root,'test-results/quiz-mobile-'+width+'.png'),fullPage:true});
  }
  await page.setViewportSize({width:1365,height:950});
  for(let i=0;i<8;i++)await page.locator('.d-quiz-question').nth(i).getByRole('radio').nth(i===0?1:i%4).check();
  await page.getByRole('button',{name:'Grade & save attempt'}).click();
  await page.getByRole('heading',{name:'Score: 7 / 8',exact:true}).waitFor();
  const scoreBounds=await page.getByRole('heading',{name:'Score: 7 / 8',exact:true}).boundingBox();
  const quizHeader=await page.locator('#activity-dialog header').boundingBox();
  assert.ok(scoreBounds.y>=quizHeader.y+quizHeader.height&&scoreBounds.y+scoreBounds.height<950,'Score is visible below the sticky dialog header');
  assert.match(await page.locator('.d-quiz-result').innerText(),/87.5% correct/);
  assert.equal(await page.locator('.d-quiz-feedback.d-ai').count(),8);
  assert.match(await page.locator('.d-quiz-feedback').first().innerText(),/Incorrect/);
  await page.screenshot({path:path.join(root,'test-results/quiz-score.png'),fullPage:true});
  await page.locator('#activity-dialog header button').click();
  await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting);
  await page.locator('#d-tab-quizzes').click();await page.locator('#quiz-history .d-quiz-attempt').nth(1).waitFor();
  const physicsAttempt=page.locator('#quiz-history .d-quiz-attempt').filter({has:page.getByRole('heading',{name:'Physics practice',exact:true})});
  assert.match(await physicsAttempt.innerText(),/7 \/ 8/);
  await physicsAttempt.getByRole('button',{name:'Review attempt'}).click();
  await page.getByRole('heading',{name:'Score: 7 / 8',exact:true}).waitFor();
  assert.match(await page.locator('.d-quiz-result .d-origin').innerText(),/gpt-6-astra/);
  await page.locator('#activity-dialog header button').click();
  await physicsAttempt.getByRole('button',{name:'Remove attempt'}).click();
  await page.waitForFunction(()=>document.querySelectorAll('#quiz-history .d-quiz-attempt').length===1);
  assert.equal((await api('/library?profile='+pid+'&kind=quiz')).activities.length,2,'Removing an attempt preserves saved quizzes');
  await page.getByRole('button',{name:'Clear history',exact:true}).click();
  await page.getByText('No quiz attempts yet. Complete a quiz to see your score here.',{exact:true}).waitFor();
  assert.equal((await api('/quiz/history?profile_id='+pid)).attempts.length,0);
  assert.equal((await api('/library?profile='+pid+'&kind=quiz')).activities.length,2);
  const manualQuiz=(await api('/library?profile='+pid+'&kind=quiz')).activities.find(item=>item.title==='Evidence quiz');
  const quizRow=page.locator('#d-content [data-activity-id="'+manualQuiz.id+'"]');
  await quizRow.getByRole('button',{name:'Start',exact:true}).click();
  await page.getByRole('radio',{name:'A traceable source'}).check();await page.getByRole('button',{name:'Grade & save attempt'}).click();
  await page.getByRole('heading',{name:'Score: 1 / 1',exact:true}).waitFor();await page.locator('#activity-dialog header button').click();
  assert.equal(quizDrafts.length,2,'Starting a saved quiz does not generate new questions');
  await assertCaptions(page,'saved quiz row actions');
  await page.screenshot({path:path.join(root,'test-results/quiz-actions-desktop.png'),fullPage:true});
  for(const width of [390,320]){
    await page.setViewportSize({width,height:900});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Quiz row actions fit at '+width);
    await page.screenshot({path:path.join(root,'test-results/quiz-actions-mobile-'+width+'.png'),fullPage:true});
  }
  await page.setViewportSize({width:1365,height:950});
  page.removeAllListeners('dialog');page.once('dialog',dialog=>dialog.dismiss());
  await quizRow.getByRole('button',{name:'Delete quiz',exact:true}).click();
  assert.equal((await api('/library?profile='+pid+'&kind=quiz')).activities.length,2);
  page.on('dialog',dialog=>dialog.accept());
  await quizRow.getByRole('button',{name:'Delete quiz',exact:true}).click();await quizRow.waitFor({state:'detached'});
  assert.equal((await api('/library?profile='+pid+'&kind=quiz')).activities.length,1);
  assert.equal((await api('/quiz/history?profile_id='+pid)).attempts.length,1,'Deleting a quiz preserves its previous scores');
  await page.locator('#quiz-history').getByRole('button',{name:'Review attempt',exact:true}).click();
  await page.getByRole('heading',{name:'Score: 1 / 1',exact:true}).waitFor();await page.locator('#activity-dialog header button').click();
  await page.locator('#d-tab-connections').click();await page.getByRole('button',{name:'Connect SQLite database'}).click();await page.getByLabel('Connection name').fill('Synthetic REI dataset');await page.getByLabel('Existing database path on this computer (optional)').fill(database);await page.getByRole('button',{name:'Connect read-only'}).click();await page.waitForSelector('#connect-dialog:not([open])',{state:'attached'});await page.getByRole('button',{name:'Browse tables'}).click();await page.getByLabel('gene',{exact:true}).check();await page.getByRole('button',{name:'Preview selected fields'}).click();await page.getByRole('cell',{name:'BRCA1'}).waitFor();await page.getByRole('button',{name:'Save this page as offline snapshot'}).click();await page.locator('#database-dialog header button').click();
  await api('/budget',{period:'monthly',token_limit:0,cost_limit:null});
  await page.locator('#connection-button').click();await page.waitForFunction(()=>D.budget?.blocked);
  assert.match(await page.locator('#ai-setup-dialog [data-ai-availability]').textContent(),/Token limit reached/);
  assert.ok(await page.locator('#connection-button').evaluate(x=>x.classList.contains('d-budget-blocked')));
  await page.getByLabel('Local-only mode — no external requests').check();await page.waitForFunction(()=>D.settings.local_only);
  await page.getByRole('button',{name:'Close AI setup',exact:true}).click();assert.equal(await page.locator('#ai-availability-notice').isVisible(),true);
  await page.reload();await page.waitForFunction(()=>D.ready&&!D.connecting&&D.settings.local_only);assert.equal(await page.evaluate(()=>D.profile.id),pid);assert.equal(await page.locator('#workspace-title').textContent(),'My physics workspace');assert.equal(await page.locator('#results-heading').isVisible(),false);assert.equal(await page.evaluate(()=>D.budget.blocked),true);
  await page.locator('#nav-library').click();await page.getByLabel('Search text and metadata').fill('Evidence notebook');await page.getByLabel('Search text and metadata').press('Tab');await page.locator('#library-dialog').getByRole('heading',{name:'Evidence notebook'}).waitFor();await page.locator('#library-dialog header button').click();
  await assertCaptions(page,'offline library');const exported=await fetch(base+'/api/discovery/archives/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile_id:pid})});assert.ok(exported.ok);const archive=await api('/archives/open',{file_base64:Buffer.from(await exported.arrayBuffer()).toString('base64')});assert.ok(archive.activities.some(x=>x.title==='Evidence notebook'));assert.ok(!archive.activities.some(x=>x.sensitive));const imported=await api('/archives/import',{id:archive.id});assert.ok(imported.skipped>=2);
  await page.screenshot({path:path.join(root,'test-results/discovery-desktop.png'),fullPage:true});
  for(const width of [390,320]){await page.setViewportSize({width,height:900});await page.locator('#profile-settings').click();await page.getByText('Profile options',{exact:true}).click();await page.getByRole('button',{name:'Edit profile',exact:true}).click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No overflow at '+width);await page.screenshot({path:path.join(root,'test-results/discovery-mobile-'+width+'.png'),fullPage:true});await page.locator('#profile-dialog header button').click();}
  assert.deepEqual(errors,[]);console.log('PASS Discovery desktop/mobile: AI model/reasoning persistence, quota notice, profiles, taxonomy, notes, 8-question AI quiz, scoring, persistent history/removal, SQLite, offline restart, ZIP roundtrip.');
}finally{if(browser)await browser.close();server.kill();await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));fs.rmSync(temporary,{recursive:true,force:true});}})().catch(e=>{console.error(e);console.error(logs.slice(-2500));process.exitCode=1;});
