// Real configuration persistence; connection checks are intercepted (no paid calls).
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawn}=require('node:child_process'),{chromium}=require('playwright');
const {assertCaptions}=require('./caption_helpers.cjs');
const root=path.resolve(__dirname,'..'),temporary=fs.mkdtempSync(path.join(os.tmpdir(),'discovery-providers-'));
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=process.env.TEST_PYTHON||(fs.existsSync(localPython)?localPython:'python'),base='http://127.0.0.1:18778';
const env={...process.env,DISCOVERY_DATA_DIR:temporary,DISCOVERY_LIBRARY_DIR:''};
for(const key of Object.keys(env))if(/^(AI_PROVIDER|OPENAI_|ANTHROPIC_|GEMINI_|DEEPSEEK_|OPENROUTER_|CUSTOM_AI_)/.test(key))delete env[key];
let server,browser,logs='';
async function start(){
  server=spawn(python,['serve_frontend.py','--port','18778','--strict-port'],{cwd:root,windowsHide:true,env,stdio:['ignore','pipe','pipe']});
  server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
  for(let i=0;i<300;i++){if(server.exitCode!==null)throw new Error(logs);try{if((await fetch(base+'/api/health')).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}
  throw new Error('Backend did not start.');
}
async function stop(){if(server&&server.exitCode===null)await new Promise(resolve=>{server.once('exit',resolve);server.kill();});}
(async()=>{try{
  await start();browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1365,height:950}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/ai/check',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({accessible:true,message:'Synthetic connection check.'})}));
  await page.route('**/api/search',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({query:route.request().postDataJSON().query,records:[],coverage:[]})}));
  const open=async()=>{await page.locator('#connection-button').click();await page.locator('#ai-provider').waitFor();await page.getByRole('heading',{name:'By profile and model',exact:true}).waitFor();};
  const connect=async()=>{await page.getByRole('button',{name:'Save & connect',exact:true}).click();await page.waitForSelector('#ai-setup-dialog:not([open])',{state:'attached'});};
  await page.goto(base);await page.waitForFunction(()=>D.ready&&state.health);await open();
  assert.equal(await page.locator('#ai-provider').inputValue(),'openai');assert.equal(await page.locator('#ai-provider option').count(),6);
  await page.getByLabel('OpenAI API key',{exact:true}).fill('sk-browser-openai-private-fixture');await connect();
  await open();await page.locator('#ai-provider').selectOption('gemini');
  assert.equal(await page.locator('#ai-api-key').inputValue(),'');assert.equal(await page.locator('#ai-api-key').getAttribute('pattern'),null);
  assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'gemini-3.8-flash');
  assert.deepEqual(await page.locator('#ai-reasoning option').evaluateAll(nodes=>nodes.map(n=>n.value)),['low','medium','high']);
  assert.equal(await page.locator('#ai-get-key').getAttribute('href'),'https://aistudio.google.com/apikey');
  await page.getByLabel('Google Gemini API key',{exact:true}).fill('AIza-browser-private-fixture');await page.locator('#ai-reasoning').selectOption('high');
  await assertCaptions(page,'Gemini connection');await connect();
  assert.deepEqual(await page.locator('#specific-reasoning option').evaluateAll(nodes=>nodes.map(n=>n.value)),['low','medium','high']);
  await open();await page.locator('#ai-provider').selectOption('deepseek');assert.equal(await page.locator('#ai-reasoning').inputValue(),'high');
  await page.locator('#ai-provider').selectOption('custom');
  assert.equal(await page.locator('#ai-base-url').isVisible(),true);assert.equal(await page.locator('#ai-reasoning').isDisabled(),true);
  assert.equal(await page.locator('#ai-get-key').isVisible(),false);
  await page.locator('#ai-base-url').fill('https://compatible.example/v1');await page.getByLabel('Model',{exact:true}).fill('org/research-model');
  await page.getByLabel('Provider API key',{exact:true}).fill('custom-browser-private-fixture');await connect();
  await open();await page.locator('#ai-base-url').fill('https://new.example/v1');
  assert.equal(await page.locator('#ai-api-key').evaluate(n=>n.required),true,'Endpoint changes require a key again');
  await page.locator('#ai-provider').selectOption('openai');assert.equal(await page.locator('#ai-api-key').evaluate(n=>n.required),false);
  assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'gpt-6-astra');await connect();
  await open();await page.locator('#ai-provider').selectOption('gemini');
  assert.equal(await page.locator('#ai-reasoning').inputValue(),'high');assert.equal(await page.locator('#ai-api-key').inputValue(),'');await connect();
  // Restart the actual backend; only its private .env restores the selection.
  await stop();await start();await page.reload();await page.waitForFunction(()=>D.ready&&state.aiStatus?.phase==='ready');await open();
  assert.equal(await page.locator('#ai-provider').inputValue(),'gemini');assert.equal(await page.locator('#ai-reasoning').inputValue(),'high');
  const health=await (await fetch(base+'/api/health')).json();assert.equal(health.ai.provider,'gemini');
  const browserData=await page.evaluate(()=>JSON.stringify({local:{...localStorage},session:{...sessionStorage}}));
  for(const secret of ['sk-browser-openai-private-fixture','AIza-browser-private-fixture','custom-browser-private-fixture']){
    assert.ok(!browserData.includes(secret));assert.ok(!JSON.stringify(health).includes(secret));
  }
  // A dated usage fixture exercises the same rendering path as persisted usage.
  await page.evaluate(()=>renderProfileModelUsage({breakdown:[{}],daily_usage:[{date:'2026-10-17',profile:'rei',model:'gemini:gemini-3.8-flash',requests:2,tokens:4321,unknown_cost:true}]}));
  assert.match(await page.locator('#ai-usage-table').innerText(),/Date \(UTC\)/);
  assert.match(await page.locator('#ai-usage-table').innerText(),/2026-10-17/);assert.match(await page.locator('#ai-usage-table').innerText(),/4,321/);
  await assertCaptions(page,'provider selection and dated usage');
  fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  for(const width of [1365,390,320]){
    await page.setViewportSize({width,height:950});
    assert.equal(await page.locator('#ai-setup-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Dialog fits at '+width);
    await page.screenshot({path:path.join(root,'test-results/ai-providers-'+width+'.png'),fullPage:true});
  }
  assert.deepEqual(errors,[]);console.log('PASS provider selection, separate keys, restart persistence, reasoning choices, dated usage, captions and mobile layout.');
}catch(error){console.error(error);process.exitCode=1;}finally{await browser?.close();await stop();fs.rmSync(temporary,{recursive:true,force:true});}})();
