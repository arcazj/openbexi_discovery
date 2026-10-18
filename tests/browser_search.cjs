// Real controls, mocked external results: no provider or public-source requests.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{
  const name=new URL(req.url,'http://localhost').pathname;
  const file=name==='/'?'index.html':/^\/assets\/[\w.-]+\.(js|css)$/.test(name)?name.slice(1):null;
  if(!file){res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');
  res.end(fs.readFileSync(path.join(root,file)));
});
let browser;
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  browser=await chromium.launch({headless:true});
  fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
  for(const width of [1365,390,320]){
    const context=await browser.newContext({viewport:{width,height:950},reducedMotion:'reduce'});
    const page=await context.newPage(),calls=[],errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    let delay=0,recordCount=0,unavailable=false;
    await page.route('**/api/**',async route=>{
      const pathname=new URL(route.request().url()).pathname;
      const json=body=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)}).catch(()=>{});
      if(pathname==='/api/health')return json({ai:{configured:true,model:'gpt-6-astra',reasoning_effort:'xhigh'}});
      if(pathname==='/api/ai/check')return json({accessible:true,model:'gpt-6-astra'});
      if(pathname!=='/api/search')return route.fulfill({status:404,body:'Not available'}).catch(()=>{});
      const body=route.request().postDataJSON();calls.push(body);
      if(delay)await new Promise(resolve=>setTimeout(resolve,delay));
      const overall=body.scope==='overall'||!body.sources.length;
      const text='A finding from a verified source. [1]';
      return json({query:body.query,scope:overall?'overall':'specific',interpretation:{type:'topic',term:body.query},
        model:'gpt-6-astra',reasoning_effort:body.reasoning_effort,records:overall?[]:Array.from({length:recordCount},(_,i)=>({id:'pubmed:'+(1000+i),source:'pubmed',type:'publication',title:'Evidence record '+(i+1),summary:'Retrieved research abstract.',url:'https://pubmed.ncbi.nlm.nih.gov/'+(1000+i)+'/',metadata:{}})),
        ...(overall?{answer:[{text,citations:[{start_index:34,end_index:37,url:'https://example.org/research',title:'Research source'}]}],
          web_sources:[{url:'https://example.org/research',title:'Research source'}]}:{}),
        coverage:overall?[{source:'web',status:'ok',retrieved:1,total:null,query:body.query}]:body.sources.map(source=>({source,
          status:unavailable?'error':'ok',retrieved:0,total:unavailable?null:0,query:source+' exact query',error:unavailable?'Unavailable fixture':undefined})),
        retrieved_at:new Date().toISOString()});
    });
    await page.goto('http://127.0.0.1:'+server.address().port);
    await page.waitForFunction(()=>state.health?.ai?.configured);
    await page.locator('#query').fill('BRCA1 research');
    assert.equal(await page.locator('#search-coverage').isVisible(),true);
    assert.equal(await page.locator('#overall-reasoning').inputValue(),'medium');
    assert.equal(await page.locator('#specific-reasoning').inputValue(),'medium');
    assert.deepEqual(await page.locator('#overall-reasoning option').allTextContents(),['Low','Medium','High','xHigh','Ultra']);
    assert.deepEqual(await page.locator('#specific-reasoning option').allTextContents(),['Low','Medium','High','xHigh','Ultra']);
    await page.locator('#overall-reasoning').selectOption('max');
    await page.locator('#specific-reasoning').selectOption('xhigh');
    assert.equal(calls.length,0,'Changing reasoning never starts a search');
    await page.locator('#source-gwas').uncheck();
    assert.equal(await page.locator('#search-selection').count(),0);
    assert.equal(await page.getByText('Search broadly, or choose sources below.',{exact:true}).count(),0);
    assert.equal(await page.locator('#search-availability').count(),0);
    await page.locator('#search-button').click();
    await page.waitForFunction(()=>state.search?.scope==='overall'&&!state.searchController);
    assert.equal(calls.at(-1).reasoning_effort,'max');assert.deepEqual(calls.at(-1).sources,[]);
    assert.equal(await page.locator('.search-answer a').getAttribute('href'),'https://example.org/research');
    assert.equal(await page.locator('#result-scope').count(),0);
    await page.locator('#specific-search-button').click();
    await page.waitForFunction(()=>state.search?.scope==='specific'&&!state.searchController);
    assert.deepEqual(calls.at(-1).sources,['pubmed','ensembl']);assert.equal(calls.at(-1).reasoning_effort,'xhigh');
    assert.equal(await page.locator('#results-heading').innerText(),'Source evidence');
    for(const id of ['coverage','coverage-details','results-tabs','search-notice'])assert.equal(await page.locator('#'+id).isVisible(),false);
    assert.equal(await page.getByRole('button',{name:'Search broadly with this prompt'}).isVisible(),true);
    await page.getByRole('button',{name:'Search broadly with this prompt'}).click();
    await page.waitForFunction(()=>state.search?.scope==='overall'&&!state.searchController);
    await page.locator('#search-clear').click();
    assert.equal(await page.locator('#search-coverage input:checked').count(),0);
    await page.locator('#specific-search-button').click();
    await page.waitForFunction(()=>!state.searchController);
    assert.deepEqual(calls.at(-1).sources,[]);assert.equal(calls.at(-1).reasoning_effort,'xhigh');
    await page.locator('#search-select-all').click();
    await page.locator('#source-gwas').uncheck();
    assert.equal(await page.locator('#search-notice').isVisible(),false);
    await page.locator('#source-gwas').check();
    unavailable=true;await page.locator('#specific-search-button').click();
    await page.waitForFunction(()=>!state.searchController);
    assert.equal(await page.locator('.coverage-item.error').count(),3);
    assert.match(await page.locator('#search-notice').innerText(),/could not be retrieved/);
    unavailable=false;delay=700;
    await page.locator('#search-button').click();await page.waitForFunction(()=>!!state.searchController);
    assert.equal(await page.locator('#specific-search-button').isDisabled(),true);
    await page.locator('#cancel-search').click();await page.waitForFunction(()=>!state.searchController);
    assert.equal(await page.locator('#query').inputValue(),'BRCA1 research');
    assert.equal(await page.locator('#overall-reasoning').inputValue(),'max');
    assert.equal(await page.locator('#specific-reasoning').inputValue(),'xhigh');
    assert.equal(await page.locator('#search-button').isEnabled(),true);delay=0;
    await page.keyboard.press('Tab');await page.locator('#specific-search-button').focus();
    await page.locator('#control-caption').waitFor({state:'visible'});
    assert.match(await page.locator('#control-caption').innerText(),/selected topics or sources/);
    await page.keyboard.press('Escape');assert.equal(await page.locator('#control-caption').isVisible(),false);
    const overall=await page.locator('#search-button').boundingBox(),specific=await page.locator('#specific-search-button').boundingBox();
    assert.ok(specific.y>overall.y);assert.ok(Math.abs(specific.x-overall.x)<1);
    const privacy=await page.locator('.d-search-privacy>summary').boundingBox();
    assert.ok(privacy.y>=specific.y+specific.height&&privacy.y-specific.y-specific.height<=6);
    assert.ok(Math.abs(privacy.x-specific.x)<1);
    assert.ok((await page.locator('#query').boundingBox()).height<=152);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    recordCount=50;await page.locator('#specific-search-button').click();
    await page.waitForFunction(()=>!state.searchController);
    assert.equal(calls.at(-1).limit,50);
    const callCount=calls.length;
    for(const count of [10,20,50]){
      await page.getByLabel('Records to show',{exact:true}).selectOption(String(count));
      assert.equal(await page.locator('.record').count(),count);
    }
    assert.equal(calls.length,callCount,'Record selector does not rerun AI or external search');
    await page.getByLabel('Records to show',{exact:true}).selectOption('10');
    await page.screenshot({path:path.join(root,'test-results','search-1.2.2-'+width+'.png'),fullPage:false});
    await page.reload();await page.waitForFunction(()=>state.health?.ai?.configured);
    assert.equal(await page.locator('#overall-reasoning').inputValue(),'max');
    assert.equal(await page.locator('#specific-reasoning').inputValue(),'xhigh');
    assert.deepEqual(errors,[]);await context.close();
    console.log('PASS search modes, reasoning, citations, fallback, cancellation, accessibility and layout at '+width+'px');
  }
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{await browser?.close();server.close();});
