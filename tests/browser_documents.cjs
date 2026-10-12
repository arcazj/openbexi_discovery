// Real document CRUD in Chromium and temporary local storage; no AI/provider calls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const {spawn}=require('node:child_process');
const {chromium}=require('playwright');
const {assertCaptions}=require('./caption_helpers.cjs');
const root=path.resolve(__dirname,'..');
const localPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const python=process.env.TEST_PYTHON||(fs.existsSync(localPython)?localPython:'python');
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'discovery-documents-'));
const port=18779,base='http://127.0.0.1:'+port;
const server=spawn(python,['serve_frontend.py','--port',String(port),'--strict-port'],{
  cwd:root,windowsHide:true,env:{...process.env,OPENAI_API_KEY:'',OPENAI_MODEL:'',OPENAI_REASONING_EFFORT:'',
    DISCOVERY_DATA_DIR:temporary,DISCOVERY_LIBRARY_DIR:''},stdio:['ignore','pipe','pipe']});
let logs='',browser;
server.stdout.on('data',data=>logs+=data);server.stderr.on('data',data=>logs+=data);
async function waitServer(){for(let i=0;i<450;i++){if(server.exitCode!==null)throw new Error(logs);try{if((await fetch(base+'/api/health')).ok)return;}catch{}await new Promise(resolve=>setTimeout(resolve,100));}throw new Error('Backend did not start: '+logs);}
async function api(route,body){const response=await fetch(base+'/api/discovery'+route,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.ok(response.ok,await response.clone().text());return response.json();}
async function documents(){return (await api('/library?kind=document')).activities;}
(async()=>{try{
  await waitServer();await api('/settings',{local_only:true});
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1365,height:950}}),errors=[];
  let searchRequests=0;page.on('request',request=>{if(request.url().endsWith('/api/search'))searchRequests++;});
  page.on('pageerror',error=>errors.push(error.message));
  const editor=page.locator('#material-dialog'),reader=page.locator('#activity-dialog');
  const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
  async function ready(){await page.waitForFunction(()=>D.ready&&!D.connecting);}
  async function closeReader(){await reader.locator('header button').click();}
  async function save(name){await button(editor,name).click();await page.waitForSelector('#material-dialog:not([open])',{state:'attached'});await reader.locator('h2').waitFor();}
  async function edit(){await button(reader,'Edit document').click();await editor.waitFor();}
  async function openLibrary(){await page.locator('#profile-settings').click();await page.locator('#nav-library').click();await page.locator('#library-dialog[open]').waitFor();}
  await page.goto(base);await ready();assert.equal(searchRequests,0,'Local-only mode prevents automatic startup searches');await page.locator('#d-tab-documents').click();
  await button(page,'New document').click();
  await button(editor,'Save locally').click();await editor.getByText('Enter a document title.',{exact:true}).waitFor();
  await editor.getByLabel('Title',{exact:true}).fill('Research draft');
  await editor.getByLabel('Content / notes',{exact:true}).fill('Literal <script>unsafe()</script> and evidence.');
  await assertCaptions(page,'new document');await save('Save locally');
  let items=await documents();assert.equal(items.length,1);const id=items[0].id;
  assert.equal(await reader.locator('.d-document').textContent(),'Literal <script>unsafe()</script> and evidence.');
  assert.equal(await reader.locator('.d-document script').count(),0);
  await edit();await editor.getByLabel('Title',{exact:true}).fill('Discarded change');
  await button(editor,'Cancel').click();assert.equal((await api('/library/'+id)).title,'Research draft');
  await edit();await editor.getByLabel('Title',{exact:true}).fill('Research revised');
  await editor.getByLabel('Content / notes',{exact:true}).fill('Updated text persists after reload.');
  await save('Save changes');assert.equal((await documents()).length,1);
  assert.equal((await api('/library/'+id)).revision,2);
  await page.reload();await ready();await page.locator('#d-tab-documents').click();
  await page.locator('#d-content .d-row').filter({hasText:'Research revised'}).getByRole('button',{name:'Open',exact:true}).click();
  await reader.getByText('Updated text persists after reload.',{exact:true}).waitFor();

  // A concurrent save must not silently overwrite another window's edits.
  await edit();await editor.getByLabel('Content / notes',{exact:true}).fill('Unsaved stale edit');
  await api('/library/'+id+'/update',{base_revision:2,title:'Research revised',content:'Saved in another window'});
  await button(editor,'Save changes').click();
  await editor.getByText('This document changed in another window. Reopen it before editing again.',{exact:true}).waitFor();
  assert.equal(await editor.getByLabel('Content / notes',{exact:true}).inputValue(),'Unsaved stale edit');
  await button(editor,'Cancel').click();await closeReader();

  await button(page,'Import file').click();
  await editor.locator('input[type=file]').setInputFiles({name:'source.md',mimeType:'text/markdown',buffer:Buffer.from('# Original text')});
  await page.waitForFunction(()=>document.querySelector('#material-dialog textarea').value==='# Original text');
  await editor.getByLabel('Content / notes',{exact:true}).fill('# Edited before import');await save('Save locally');
  const attached=(await documents()).find(item=>item.title==='source.md');assert.ok(attached);
  assert.equal(await (await fetch(base+'/api/discovery/library/'+attached.id+'/file')).text(),'# Edited before import');
  await edit();await editor.getByLabel('Content / notes',{exact:true}).fill('# Edited after import');await save('Save changes');
  const downloading=page.waitForEvent('download');await button(reader,'Download document file').click();
  const downloaded=await downloading;assert.equal(downloaded.suggestedFilename(),'source.md');
  assert.equal(fs.readFileSync(await downloaded.path(),'utf8'),'# Edited after import');

  const pdf=Buffer.from('%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Count 0 /Kids [] >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF');
  await edit();await editor.locator('input[type=file]').setInputFiles({name:'paper.PDF',mimeType:'application/pdf',buffer:pdf});
  await editor.getByLabel('Content / notes',{exact:true}).fill('Notes accompanying the PDF.');await save('Save changes');
  await reader.getByText('Notes accompanying the PDF.',{exact:true}).waitFor();
  assert.equal(await reader.locator('iframe.d-pdf').count(),1);
  await edit();await editor.getByLabel('Title',{exact:true}).fill('PDF with notes');
  await editor.getByLabel('Content / notes',{exact:true}).fill('Updated PDF notes.');
  await assertCaptions(page,'edit document');
  fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  await page.screenshot({path:path.join(root,'test-results/documents-desktop.png'),fullPage:true});
  for(const width of [390,320]){
    await page.setViewportSize({width,height:900});
    assert.equal(await editor.evaluate(node=>node.scrollWidth>node.clientWidth),false,'Document editor fits at '+width);
    await page.screenshot({path:path.join(root,'test-results/documents-mobile-'+width+'.png'),fullPage:true});
  }
  await page.setViewportSize({width:1365,height:950});await save('Save changes');
  assert.deepEqual(Buffer.from(await (await fetch(base+'/api/discovery/library/'+attached.id+'/file')).arrayBuffer()),pdf);
  await reader.getByText('Updated PDF notes.',{exact:true}).waitFor();
  await edit();await editor.locator('input[type=file]').setInputFiles({name:'invalid.exe',mimeType:'application/octet-stream',buffer:Buffer.from('invalid')});
  await editor.getByText('Choose a PDF, Markdown, text, or JSON file.',{exact:true}).waitFor();
  assert.equal(await button(editor,'Save changes').isDisabled(),true);await button(editor,'Cancel').click();await closeReader();

  // A document from another profile can be edited through Local library, retaining its original profile.
  const bootstrap=await api('/bootstrap');
  const other=await api('/profiles/save',{profile:{...bootstrap.profiles[0],name:'Other document workspace'},create:true});
  await api('/profiles/action',{id:other.id,revision:other.revision,action:'activate'});
  await page.reload();await ready();await openLibrary();
  const list=page.locator('#library-dialog');
  await list.getByLabel('Search text and metadata',{exact:true}).fill('Research revised');
  await list.getByLabel('Search text and metadata',{exact:true}).press('Tab');
  await page.waitForFunction(()=>document.querySelectorAll('#library-dialog .d-row').length===1);
  await list.getByRole('heading',{name:'Research revised',exact:true}).waitFor();
  await button(list.locator('.d-row').filter({has:page.getByRole('heading',{name:'Research revised',exact:true})}),'Open').click();await edit();await editor.getByLabel('Title',{exact:true}).fill('Research final');await save('Save changes');
  assert.equal((await api('/library/'+id)).profile_id,'rei');await closeReader();
  assert.equal(await list.locator('.d-row').count(),0,'Edited document leaves the old search results immediately');
  await list.getByLabel('Search text and metadata',{exact:true}).fill('Research final');
  await list.getByLabel('Search text and metadata',{exact:true}).press('Tab');
  await list.getByRole('heading',{name:'Research final',exact:true}).waitFor();await button(list.locator('.d-row').filter({has:page.getByRole('heading',{name:'Research final',exact:true})}),'Open').click();
  page.once('dialog',dialog=>dialog.dismiss());await button(reader,'Delete local activity').click();
  assert.equal((await documents()).length,2,'Canceling deletion preserves the document');
  page.once('dialog',dialog=>dialog.accept());await button(reader,'Delete local activity').click();
  await page.waitForSelector('#activity-dialog:not([open])',{state:'attached'});
  await page.waitForFunction(()=>document.querySelectorAll('#library-dialog .d-row').length===0);
  assert.equal((await documents()).length,1);
  assert.equal((await fetch(base+'/api/discovery/library/'+id)).status,404);
  await list.locator('header button').click();

  // ZIP preview stays read-only, with the current PDF and its notes intact.
  const exported=await fetch(base+'/api/discovery/archives/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({activity_id:attached.id})});
  assert.ok(exported.ok);const archive=await api('/archives/open',{file_base64:Buffer.from(await exported.arrayBuffer()).toString('base64')});
  await page.evaluate(async archive=>{await openActivity(archive.activities[0].id,archive);},archive);
  assert.equal(await button(reader,'Edit document').count(),0);assert.equal(await button(reader,'Delete local activity').count(),0);
  await reader.getByText('Updated PDF notes.',{exact:true}).waitFor();await closeReader();
  await page.evaluate(async id=>{await openActivity(id);},attached.id);
  page.once('dialog',dialog=>dialog.accept());await button(reader,'Delete local activity').click();
  await page.waitForSelector('#activity-dialog:not([open])',{state:'attached'});
  assert.equal((await fetch(base+'/api/discovery/library/'+attached.id+'/file')).status,404);
  assert.equal((await documents()).length,0);
  // Read-only previews must preserve Windows line endings and the unseen tail when renamed.
  const fullText='Windows line\r\n'.repeat(20000)+'Unseen tail';
  const large=await api('/library',{profile_id:other.id,kind:'document',title:'Large sensitive file',
    filename:'large.txt',file_base64:Buffer.from(fullText).toString('base64'),sensitive:true,consent_local:true});
  await page.evaluate(async id=>{await openActivity(id);},large.id);await edit();
  assert.equal(await editor.getByLabel('Content / notes',{exact:true}).getAttribute('readonly'),'');
  assert.equal(await editor.getByLabel('Contains sensitive information',{exact:true}).isDisabled(),true);
  await editor.getByLabel('Title',{exact:true}).fill('Large sensitive renamed');await button(editor,'Save changes').click();
  await editor.getByText('Confirm retention of this sensitive document.',{exact:true}).waitFor();
  await editor.getByLabel('I authorize saving this sensitive material on this computer',{exact:true}).check();await save('Save changes');
  assert.equal(await (await fetch(base+'/api/discovery/library/'+large.id+'/file')).text(),fullText);
  page.once('dialog',dialog=>dialog.accept());await button(reader,'Delete local activity').click();
  await page.waitForSelector('#activity-dialog:not([open])',{state:'attached'});
  assert.equal((await documents()).length,0);assert.deepEqual(errors,[]);
  console.log('PASS document CRUD: create, read, edit, import/replace/download files, PDF notes, persistence, conflicts, cross-profile library refresh, delete, read-only ZIP, desktop/mobile.');
}finally{if(browser)await browser.close();server.kill();await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));fs.rmSync(temporary,{recursive:true,force:true});}})().catch(error=>{console.error(error);process.exitCode=1;});
