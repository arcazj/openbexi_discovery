const assert=require('node:assert/strict');

// Exercise the common request path with held synthetic responses. No provider calls.
async function assertAIWorkProgress(page){
  await page.locator('dialog[open] header button').last().click();
  const tasks=[
    {id:'guidance',url:'/api/ai',body:{action:'guidance'},label:'Preparing research guidance'},
    {id:'explain',url:'/api/ai',body:{action:'explain'},label:'Explaining source evidence'},
    {id:'questions',url:'/api/ai',body:{action:'questions'},label:'Developing research questions'},
    {id:'compare',url:'/api/ai',body:{action:'compare'},label:'Comparing research briefs'},
    {id:'quiz',url:'/api/discovery/ai/draft',body:{task:'create_quiz'},label:'Creating an 8-question quiz'},
    {id:'create',url:'/api/discovery/ai/draft',body:{task:'create_profile'},label:'Drafting profile wording'},
    {id:'wording',url:'/api/discovery/ai/draft',body:{task:'update_profile'},label:'Updating profile wording'},
    {id:'profile',url:'/api/discovery/ai/draft',body:{task:'adapt_profile'},label:'Preparing profile preview'},
    {id:'answer',url:'/api/discovery/ai/draft',body:{task:'answer'},label:'Preparing an AI answer'},
    {id:'apis',url:'/api/discovery/api-connections/recommend',body:{},label:'Finding API recommendations'},
    {id:'dataset',url:'/api/discovery/datasets/fixture/ask',body:{},label:'Analyzing your reviewed dataset'},
    {id:'check',url:'/api/ai/check',body:{},label:'Checking AI connection'},
    {id:'configure',url:'/api/ai/configure',body:{},label:'Saving AI connection settings'}
  ];
  const routes=new Map();
  await page.route('**/api/**?progress_fixture=*',route=>routes.set(new URL(route.request().url()).searchParams.get('progress_fixture'),route));
  await page.evaluate(tasks=>{
    window.progressFixture={controllers:{},promises:{},outcomes:{}};
    for(const task of tasks){
      const controller=new AbortController();progressFixture.controllers[task.id]=controller;
      progressFixture.promises[task.id]=fetchBounded(endpoint(task.url)+'?progress_fixture='+task.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(task.body)},120000,controller.signal)
        .then(()=>progressFixture.outcomes[task.id]='done',e=>progressFixture.outcomes[task.id]=e.name);
    }
  },tasks);
  await page.waitForFunction(count=>document.querySelectorAll('#ai-work-status [role=progressbar]').length===count,tasks.length);
  assert.equal(await page.locator('#ai-work-status').count(),1,'Concurrent requests share one indicator');
  assert.ok(await page.locator('#ai-work-status').evaluate(n=>n.parentElement===document.body),'Progress floats on the main page');
  for(const task of tasks)assert.equal(await page.getByRole('progressbar',{name:task.label,exact:true}).count(),1,task.id+' has a labeled progress bar');
  await page.locator('#profile-settings').click();
  await page.locator('#profile-dialog #ai-work-status').waitFor();
  await page.setViewportSize({width:320,height:740});
  assert.equal(await page.locator('#profile-dialog').evaluate(n=>n.scrollWidth>n.clientWidth),false,'Concurrent progress fits a mobile dialog');
  const bounds=await page.locator('#ai-work-status').boundingBox();assert.ok(bounds&&bounds.y>=0&&bounds.y+bounds.height<=740);
  await page.locator('#profile-dialog header button').click();
  await page.waitForFunction(()=>document.querySelector('#ai-work-status')?.parentElement===document.body);
  await routes.get('guidance').fulfill({contentType:'application/json',body:'{}'});
  await page.waitForFunction(()=>progressFixture.outcomes.guidance==='done');
  assert.equal(await page.getByRole('progressbar').count(),tasks.length-1,'One completed task does not hide other pending work');
  await routes.get('apis').fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Synthetic AI failure'})});
  await page.waitForFunction(()=>!!progressFixture.outcomes.apis);
  assert.equal(await page.getByRole('progressbar',{name:'Finding API recommendations'}).count(),0,'Failure removes its indicator');
  await page.evaluate(()=>progressFixture.controllers.dataset.abort());
  await page.waitForFunction(()=>progressFixture.outcomes.dataset==='AbortError');
  assert.equal(await page.getByRole('progressbar',{name:'Analyzing your reviewed dataset'}).count(),0,'Cancellation removes its indicator');
  await Promise.all([...routes].filter(([id])=>!['guidance','apis'].includes(id)).map(([,route])=>route.fulfill({contentType:'application/json',body:'{}'}).catch(()=>{})));
  await page.evaluate(()=>Promise.all(Object.values(progressFixture.promises)));
  await page.locator('#ai-work-status').waitFor({state:'detached'});
  // A bounded timeout must clean up the shared panel as well.
  await page.evaluate(()=>{
    progressFixture.promises.timeout=fetchBounded(endpoint('/api/ai/check')+'?progress_fixture=timeout',{},200)
      .catch(e=>progressFixture.outcomes.timeout=e.name);
  });
  await page.waitForFunction(()=>progressFixture.outcomes.timeout==='AbortError');
  assert.equal(await page.locator('#ai-work-status').count(),0);
  await routes.get('timeout')?.fulfill({contentType:'application/json',body:'{}'}).catch(()=>{});
  await page.unroute('**/api/**?progress_fixture=*');
}

module.exports={assertAIWorkProgress};
