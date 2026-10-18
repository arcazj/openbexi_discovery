'use strict';

const SEARCH_LEVELS=['low','medium','high'];
function syncSearchControls(){
  if(![10,20,50].includes(Number($('limit').value)))$('limit').value='10';
  for(const scope of ['overall','specific']){
    const value=state.prefs.searchReasoning?.[scope];
    $(scope+'-reasoning').value=SEARCH_LEVELS.includes(value)?value:'medium';
  }

}
function resizeSearchPrompt(){const input=$('query');input.style.height='auto';input.style.height=Math.min(152,Math.max(76,input.scrollHeight))+'px';}
function searchBusy(busy){
  for(const id of ['search-button','specific-search-button','overall-reasoning','specific-reasoning'])$(id).disabled=busy;
  $('cancel-search').hidden=!busy;$('loading').hidden=!busy;
  $('search-form').setAttribute('aria-busy',String(busy));
}
runSearch=async function(queryOverride=null,requestedScope='overall',options={}){
  if(state.searchController)return;
  const query=(queryOverride??$('query').value).trim().replace(/\s+/g,' ');
  if(!query||query.length>250){toast('Enter a question of up to 250 characters.');$('query').focus();return;}
  const selected=selectedSources(),scope=requestedScope==='specific'&&selected.length?'specific':'overall';
  const sources=scope==='specific'?selected:[],mode=scope==='overall'?'auto':$('mode').value,limit=50;
  const effort=$(requestedScope+'-reasoning').value;
  cancelAI();cancelGuidance();
  const controller=new AbortController();state.searchController=controller;searchBusy(true);
  state.prefs={...state.prefs,sources:sourcePreferences(),mode,limit:Number($('limit').value)};persistPrefs();
  if(!$('d-sensitive').checked)remember(query);
  state.filter='all';state.search=null;state.lastAi=null;updateGuidance();
  $('welcome').hidden=true;$('results-list').replaceChildren();
  for(const id of ['coverage','coverage-details','results-tabs','ai-output'])$(id).hidden=true;
  $('results-heading').parentElement.hidden=false;
  $('results-heading').textContent=scope==='overall'?'Searching broadly':'Searching selected sources';$('result-count').textContent='';setNotice('');
  $('loading').lastElementChild.textContent=scope==='overall'?'Searching the web with GPT-6 Astra…':'Searching '+sources.map(s=>sourceNames[s]).join(', ')+'…';
  try{
    let result;
    if(state.health){
      const payload={query,mode,sources,limit,...(options.automatic?{}:{scope:requestedScope,reasoning_effort:effort})};
      const response=await fetchBounded(endpoint('/api/search'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)},310000,controller.signal);
      result=await response.json();
    }else{
      if(scope==='overall')throw new Error('Overall Search needs the local app connected to GPT-6 Astra. Select sources and use Specific Search for direct evidence browsing.');
      if($('d-sensitive').checked&&!await reviewSensitiveRequest({scope,query,sources}))throw new Error('Sensitive search canceled.');
      if(controller.signal.aborted)return;
      result=await browserSearch(query,mode,sources,limit,controller.signal);
      result.search_note='Direct source search. Connect AI to refine queries with the selected reasoning level.';
    }
    if(controller.signal.aborted||state.searchController!==controller)return;
    if(!Array.isArray(result.records)||!Array.isArray(result.coverage))throw new Error('The service returned an unsupported search result.');
    state.search={...result,scope:result.scope||scope,query:result.query||query,interpretation:result.interpretation||inferred(query,mode),filters:{mode,limit,sources:[...sources]},demo:!!result.demo};
    renderSearch();updateGuidance();
  }catch(error){
    if(state.searchController!==controller)return;
    setNotice(controller.signal.aborted?'Search canceled.':error.name==='AbortError'?'Search timed out. Try a lower reasoning level or a narrower prompt.':error.message,controller.signal.aborted?'info':'error');
    $('results-heading').textContent=controller.signal.aborted?'Search canceled':'Search unavailable';
  }finally{
    if(state.searchController===controller){state.searchController=null;searchBusy(false);syncSearchControls();}
  }
};

const renderAllRecords=renderRecords;
renderRecords=function(){
  renderAllRecords();$('results-tabs').hidden=true;
  [...$('results-list').querySelectorAll('.record')].slice(Number($('limit').value)||10).forEach(node=>node.remove());
};

const renderEvidenceSearch=renderSearch;
renderSearch=function(){
  renderEvidenceSearch();
  const result=state.search;
  if(!result)return;
  // Routine coverage metadata remains in the saved result, outside the main UI.
  $('coverage').hidden=true;$('coverage-details').hidden=true;$('results-tabs').hidden=true;
  if(!$('search-notice').classList.contains('error')&&!result.coverage.some(c=>c.status==='error'))setNotice('');
  if(result.scope==='overall'&&result.answer){
    $('results-heading').textContent='Source evidence';$('result-count').textContent=result.web_sources.length+' cited sources';$('results-tabs').hidden=true;
    setNotice('');const box=el('section',{class:'search-answer','aria-label':'AI search answer'});
    for(const part of result.answer){
      const paragraph=el('p'),text=Array.from(part.text);let cursor=0;
      for(const citation of [...part.citations].sort((a,b)=>a.start_index-b.start_index)){
        if(citation.start_index<cursor)continue;
        paragraph.append(text.slice(cursor,citation.start_index).join(''));
        const index=result.web_sources.findIndex(s=>s.url===citation.url)+1;
        paragraph.append(externalLink('['+index+']',citation.url));cursor=citation.end_index;
      }
      paragraph.append(text.slice(cursor).join(''));box.append(paragraph);
    }
    box.append(el('small',{text:'AI-generated answer · '+result.model+' · '+result.reasoning_effort+' reasoning'}));
    const links=el('ul',{class:'web-source-list'});
    result.web_sources.slice(0,Number($('limit').value)||10).forEach((source,i)=>links.append(el('li',{},externalLink('['+(i+1)+'] '+source.title,source.url))));
    $('results-list').replaceChildren(box,links);
  }else if(!result.records.length&&result.scope==='specific'){
    $('results-list').append(el('button',{class:'small',text:'Search broadly with this prompt',on:{click:()=>runSearch(result.query,'overall')}}));
  }
};

(() => {
  sourceNames.web='Web';
  $('search-source-choices').append(document.querySelector('.source-choices'));
  const limit=$('limit');
  limit.replaceChildren(...[10,20,50].map(value=>el('option',{value,text:value+' records'})));
  limit.value=[10,20,50].includes(Number(state.prefs.limit))?state.prefs.limit:10;
  limit.className='result-limit';limit.setAttribute('aria-label','Records to show');
  document.querySelector('label[for="limit"]').remove();
  $('results-heading').parentElement.append(limit);
  limit.addEventListener('change',()=>{if(state.search)renderSearch();});
  $('specific-search-button').addEventListener('click',()=>runSearch(null,'specific'));
  for(const scope of ['overall','specific'])$(scope+'-reasoning').addEventListener('change',()=>{
    state.prefs.searchReasoning={...state.prefs.searchReasoning,[scope]:$(scope+'-reasoning').value};persistPrefs();
  });
  for(const [id,checked]of [['search-select-all',true],['search-clear',false]])$(id).addEventListener('click',()=>{
    for(const source of ['pubmed','ensembl','gwas'])if(!$('source-'+source).closest('.source-chip').hidden)$('source-'+source).checked=checked;
    state.prefs.sources=sourcePreferences();persistPrefs();syncSearchControls();
    if(typeof D!=='undefined'&&D.ready&&D.tab==='sources'){resetTabBodies();selectTab('sources');}
  });
  for(const source of ['pubmed','ensembl','gwas'])$('source-'+source).addEventListener('change',syncSearchControls);
  new MutationObserver(syncSearchControls).observe($('search-source-choices'),{subtree:true,attributes:true,attributeFilter:['hidden']});
  window.addEventListener('discovery-backend-ready',syncSearchControls);
  $('query').addEventListener('input',resizeSearchPrompt);
  $('query').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('search-form').requestSubmit();}});
  $('query').placeholder='e.g. Find research linking BRCA1 variants to breast cancer';
  syncSearchControls();resizeSearchPrompt();
})();
