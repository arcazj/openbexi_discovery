// Real app shutdown/relaunch and a fresh browser; no AI or external searches.
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process'),{chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),temporary=fs.mkdtempSync(path.join(os.tmpdir(),'discovery-profile-persistence-'));
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=process.env.TEST_PYTHON||(fs.existsSync(localPython)?localPython:'python');
let server,browser,base,logs='';const errors=[];

async function start(){
  let output='';base=null;
  server=spawn(python,['run_discovery.py','--port','0'],{cwd:root,windowsHide:true,
    env:{...process.env,DISCOVERY_DATA_DIR:temporary,DISCOVERY_LIBRARY_DIR:'',OPENAI_API_KEY:'',PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe']});
  server.stdout.on('data',chunk=>{output+=chunk;logs+=chunk;const match=output.match(/full application: (http:\/\/127\.0\.0\.1:\d+)/);if(match)base=match[1];});
  server.stderr.on('data',chunk=>logs+=chunk);
  for(let i=0;i<300;i++){
    if(server.exitCode!==null)throw new Error(logs);
    try{if(base&&(await fetch(base+'/api/health')).ok)return;}catch{}
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  throw new Error('Application did not start: '+logs);
}
async function stop(){
  await browser?.close();browser=null;
  if(server&&server.exitCode===null){server.kill();await new Promise(resolve=>server.once('exit',resolve));}
}
async function api(route,body){
  const response=await fetch(base+'/api/discovery'+route,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  assert.ok(response.ok,await response.clone().text());return response.json();
}
async function open(){
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1365,height:950}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/api/search',route=>{errors.push('Unexpected startup search');return route.abort();});
  await page.goto(base);await page.waitForFunction(()=>D.hydrated&&!D.suppressSave);
  return page;
}
async function select(page,id){
  await page.locator('#profile-settings').click();await page.getByLabel('Current profile',{exact:true}).selectOption(id);
  await page.waitForFunction(id=>D.profile.id===id&&!D.switching&&!document.querySelector('#profile-dialog').open,id);
  assert.equal((await api('/bootstrap')).settings.active_profile,id);
  const settings=JSON.parse(fs.readFileSync(path.join(temporary,'.discovery','settings.json'),'utf8'));
  assert.equal(settings.active_profile,id,'Selection is saved to disk before returning to the workspace');
}
async function assertRestored(page,profile){
  assert.equal(await page.evaluate(()=>D.profile.id),profile.id);
  assert.equal(await page.locator('#active-profile-name').innerText(),'Profile: '+profile.name);
  assert.equal(await page.locator('#workspace-title').innerText(),profile.ui.eyebrow);
  assert.equal(await page.locator('#search-page').isVisible(),true);
  await page.locator('#profile-settings').click();assert.equal(await page.getByLabel('Current profile',{exact:true}).inputValue(),profile.id);
  await page.locator('#profile-dialog header button').click();
}

(async()=>{try{
  await start();await api('/settings',{local_only:true});
  const template=await api('/templates/cosmologie');
  const custom=await api('/profiles/save',{profile:{...template,name:'Astrophysics research',ui:{...template.ui,eyebrow:'Astrophysics workspace'}},create:true});
  let page=await open();await select(page,custom.id);
  await page.locator('#query').fill('Resume my research on dark energy');
  await page.locator('#overall-reasoning').selectOption('max');await page.locator('#specific-reasoning').selectOption('xhigh');
  await page.locator('#search-clear').click();await page.getByLabel('Dark energy',{exact:true}).check();
  await page.waitForFunction(async id=>{const r=await fetch('/api/discovery/workspace/'+id),w=await r.json();return w.data.query==='Resume my research on dark energy'&&w.data.prefs.searchReasoning?.overall==='max'&&w.data.prefs.searchTopics?.join(',')==='02.03.03.04';},custom.id);
  await stop();await start();page=await open();await assertRestored(page,custom);
  await page.locator('#search-topic-choices input').first().waitFor();
  assert.equal(await page.locator('#query').inputValue(),'Resume my research on dark energy');
  assert.equal(await page.locator('#overall-reasoning').inputValue(),'max');assert.equal(await page.locator('#specific-reasoning').inputValue(),'xhigh');
  assert.deepEqual(await page.evaluate(()=>selectedSearchTopics()),['02.03.03.04']);
  const saved=(await api('/bootstrap')).profiles.find(p=>p.id===custom.id);assert.deepEqual(saved,custom,'Launch preserves the complete profile');
  // Last selection wins for a bundled profile too; it needs no separate Save button.
  const cosmologie=(await api('/bootstrap')).profiles.find(p=>p.id==='cosmologie');await select(page,cosmologie.id);
  await stop();await start();page=await open();await assertRestored(page,cosmologie);
  assert.equal(await page.locator('#query').inputValue(),'','Workspace drafts stay isolated by profile');
  assert.deepEqual(errors,[]);
  console.log('PASS selected custom and bundled profiles survive full app/browser relaunch; names, topics, reasoning and saved drafts return.');
}finally{await stop();fs.rmSync(temporary,{recursive:true,force:true});}})().catch(error=>{console.error(error);console.error(logs.slice(-3000));process.exitCode=1;});
