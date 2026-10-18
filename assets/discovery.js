'use strict';
// The legacy evidence workflow remains in index.html; Discovery owns its new services.
const D={ready:false,profiles:[],profile:null,settings:{local_only:false},budget:null,levels:[],tools:{},tab:'evidence',workspaceRevision:0,saveQueue:Promise.resolve(),suppressSave:false,states:new Map(),draft:null,dirty:false,archive:null,aiControllers:new Set()};
const clone=value=>JSON.parse(JSON.stringify(value));
const dnode=(tag,props={},children=[])=>el(tag,props,children);
function sourceVisible(profile,id){return !(profile?.hidden_source_ids||[]).includes(id);}
function dstatus(node,message,error=false){node.textContent=message;node.dataset.error=String(error);}
function dbutton(text,action,cls='small'){return dnode('button',{type:'button',class:cls,text,on:{click:async event=>{const button=event.currentTarget;button.disabled=true;try{await action(event);}catch(e){toast(e.message);}finally{button.disabled=false;}}}});}
function dfield(label,value='',type='text'){const input=dnode(type==='textarea'?'textarea':'input',type==='textarea'?{}:{type});input.value=value;const wrapper=dnode('label',{},[label,input]);return {input,wrapper};}
function dcheck(label,checked=false){const input=dnode('input',{type:'checkbox'});input.checked=checked;return {input,wrapper:dnode('label',{class:'d-check'},[input,label])};}
function dselect(label,options,value){const input=dnode('select',{'aria-label':label},options.map(x=>dnode('option',{value:Array.isArray(x)?x[0]:x,text:Array.isArray(x)?x[1]:x})));input.value=value;return {input,wrapper:dnode('label',{},[label,input])};}
function drawer(title,id='discovery-dialog'){let dialog=$(id);if(!dialog){dialog=dnode('dialog',{id,class:'d-drawer'});document.body.append(dialog);}dialog.replaceChildren();const body=dnode('div',{class:'d-body'});const heading=dnode('h2',{id:id+'-title',text:title});dialog.setAttribute('aria-labelledby',heading.id);dialog.append(dnode('header',{},[heading,dbutton('×',()=>{if(D.dirty&&['profile-dialog','themes-dialog'].includes(id)&&!confirm('Discard unsaved profile changes?'))return;D.dirty=false;dialog.close();},'quiet d-close')]),body);dialog.oncancel=event=>{if(D.dirty&&['profile-dialog','themes-dialog'].includes(id)&&!confirm('Discard unsaved profile changes?'))event.preventDefault();else D.dirty=false;};if(!dialog.open)dialog.showModal();return {dialog,body};}
const legacyFetchBounded=fetchBounded;
fetchBounded=async function(url,options={},timeout=18000,parentSignal){
  const target=new URL(url,location.href),searchRequest=target.pathname==='/api/search'&&!!JSON.parse(options.body||'{}').scope,aiRequest=target.pathname==='/api/ai'||searchRequest,aiDraft=/^\/api\/discovery\/(ai\/draft$|api-connections\/recommend$|datasets\/[^/]+\/ask$|library\/[^/]+\/analyze$)/.test(target.pathname);
  if(D.ready&&D.settings.local_only&&(target.origin!==new URL(endpoint('/'),location.href).origin||['/api/search','/api/ai','/api/ai/check'].includes(target.pathname)))throw new Error('Local-only mode: use saved material in Local library.');
  if(aiRequest&&(D.ready||searchRequest)){const body=JSON.parse(options.body);body.profile_id=D.profile?.id||'rei';body.profile_revision=D.profile?.revision;body.sensitive=!!$('d-sensitive').checked;body.consent_ai=!body.sensitive||await reviewSensitiveRequest(body);if(!body.consent_ai)throw new Error('Sensitive AI request canceled.');options={...options,body:JSON.stringify(body)};}
  try{return await legacyFetchBounded(url,options,timeout,parentSignal);}catch(error){if(/AI paused|allowance|limit reached/.test(error.message)){D.lastBudgetError=error.message;updateBudgetBadge();}throw error;}finally{if(D.ready&&(aiRequest||aiDraft))refreshBudget().catch(()=>{});}
};
async function dapi(path,body,options={}){const response=await fetchBounded(endpoint('/api/discovery'+path),body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},options.timeout||20000,options.signal);return options.raw?response:response.json();}
async function dbase64(file){if(file.size>32*1024*1024)throw new Error('Choose a file smaller than 32 MB.');return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('File could not be read.'));reader.readAsDataURL(file);});}
function originLabel(item){const p=item.provenance||{};return p.origin==='ai'||p.origin==='ai_edited'?`${p.origin==='ai_edited'?'AI-assisted, user-edited':'AI generated'} · ${p.model||'model unknown'} · ${formatDate(p.generated_at)}`:p.origin==='user'?'User-provided · upstream AI origin unverified':p.origin==='template'?'Application template':'Source content · origin unverified';}
function decorate(node,provenance){node.dataset.provenance=provenance?.origin||'template';node.title=originLabel({provenance});}
async function reviewSensitiveRequest(payload){
  const {body,dialog}=drawer('Review sensitive AI request','sensitive-dialog');
  body.append(dnode('p',{text:'The exact request below will be sent to '+(payload.scope?(state.health?.ai?.configured?'GPT-6 Astra and the requested external search sources':'the selected external search sources'):(state.health?.ai?.model||'the configured AI model'))+'. Routine history omits sensitive request and response bodies.'}),dnode('pre',{text:JSON.stringify(payload,null,2)}));
  return new Promise(resolve=>{let authorized=false;dialog.addEventListener('close',()=>resolve(authorized),{once:true});body.append(dbutton('Send this request',()=>{authorized=true;dialog.close();},'primary'),dbutton('Cancel',()=>dialog.close()));});
}
async function requiresLocal(){
  if(HOSTED_DEMO)throw new Error('Run OpenBEXI Discovery locally to use profiles and the library.');
  if(D.connecting)return D.connecting;
  if(D.ready)return;
  D.connecting=(async()=>{
    if(!state.health)await checkHealth();
    if(!state.health)throw new Error('In IntelliJ, run OpenBEXI Discovery or backend/app.py, then open the HTTP URL printed in Run. You can also run: py run_discovery.py');
    await hydrateDiscovery();
  })().finally(()=>D.connecting=null);
  return D.connecting;
}
function captureWorkspace(){return {sensitive:!!D.sensitive,workspace:clone(state.workspace),prefs:{sources:sourcePreferences(),limit:Number($('limit').value),mode:$('mode').value,recent:state.prefs.recent,searchReasoning:state.prefs.searchReasoning},query:$('query').value};}
function queueWorkspace(){if(!D.ready||D.suppressSave)return;const pid=D.profile.id,data=captureWorkspace();D.saveQueue=D.saveQueue.catch(()=>{}).then(async()=>{const result=await dapi('/workspace',{profile_id:pid,revision:D.workspaceRevision,data});if(D.profile.id===pid)D.workspaceRevision=result.revision;}).catch(error=>{D.saveError=error;toast('Workspace save failed: '+error.message);throw error;});D.saveQueue.catch(()=>{});}
const legacyPersistWorkspace=persistWorkspace;
persistWorkspace=function(){if(!D.ready)return legacyPersistWorkspace();state.workspace.app_version=VERSION;state.workspace.updated_at=now();renderSaved();updateGuidance({auto:true});queueWorkspace();return true;};
const legacyPersistPrefs=persistPrefs;
persistPrefs=function(){legacyPersistPrefs();if(D.ready)queueWorkspace();};
const legacyRunSearch=runSearch;
runSearch=async function(queryOverride=null,scope='overall',options={}){
  if(D.settings.local_only){toast('Local-only mode is on. Search saved material in Local library.');return;}
  const pid=D.profile?.id,sensitive=!!D.sensitive,previous=state.search,sequence=D.searchSequence=(D.searchSequence||0)+1;
  if(D.ready)selectTab('evidence');
  const pending=legacyRunSearch(queryOverride,scope,options);
  if(state.searchController)window.dispatchEvent(new Event('discovery-search-started'));
  await pending;
  const result=state.search;
  if(D.ready&&D.profile.id===pid&&sequence===D.searchSequence&&result&&result!==previous&&!result.demo){
    try{
      await dapi('/library',{profile_id:pid,kind:'search',title:sensitive?'Sensitive search':'Search: '+result.query,request:sensitive?'[sensitive query omitted]':result.query,payload:sensitive?{omitted:'Sensitive search content excluded'}:result,provenance:result.model?{origin:'ai',model:result.model,generated_at:result.retrieved_at}:{origin:'unverified'}});
      window.dispatchEvent(new Event('discovery-search-saved'));queueWorkspace();
    }catch(error){toast('Search completed; archive save failed: '+error.message);}
  }
};
const legacyGuidanceContext=guidanceContext;
guidanceContext=function(){const result=legacyGuidanceContext();if(result&&D.ready)result.key+=JSON.stringify({profile:D.profile.id,revision:D.profile.revision,sensitive:D.sensitive});return result;};
const legacyFallbackGuidance=fallbackGuidance;
fallbackGuidance=function(){const value=legacyFallbackGuidance();if(D.ready&&!state.search)return {...value,next:D.profile.ui.guidance_text,tip:D.profile.ui.tip_text};return value;};
const legacyCheckAI=checkAIConnection;
checkAIConnection=async function(...args){if(D.ready&&(D.settings.local_only||D.budget?.blocked)){updateBudgetBadge();return false;}return legacyCheckAI(...args);};

const legacyRenderGuidance=renderGuidance;
renderGuidance=function(...args){const value=legacyRenderGuidance(...args);if(D.ready){for(const [id,key]of [['guidance-next','guidance_text'],['guidance-tip','tip_text']])decorate($(id),!state.search?D.profile.provenance[key]:null);}return value;};

function updateBudgetBadge(){
  const blocked=!!D.budget?.blocked||!!D.lastBudgetError,local=D.settings.local_only,button=$('connection-button');
  button.classList.toggle('d-budget-blocked',blocked||!!state.aiQuotaError);
  state.aiPauseReason=blocked?(D.lastBudgetError||'AI paused — '+D.budget.reason+'.')+(D.budget?.reset_at?' Local allowance resets '+new Date(D.budget.reset_at).toLocaleString()+'.':''):'';
  renderAIAvailability();
  if(blocked||local||state.aiQuotaError){
    const message=blocked?'AI paused — usage limit reached':local?'Local-only mode':'AI tokens unavailable';
    if(blocked||local)state.aiStatus={phase:'paused',message};
    $('connection-label').textContent=message;$('connection-short-label').textContent=message;
    button.title=state.aiQuotaError||state.aiPauseReason||message;button.setAttribute('aria-label',message+'. Open AI connection settings.');
    if(blocked||local)$('provenance-model').textContent=message+'.';button.dataset.state=blocked||state.aiQuotaError?'error':'offline';
    $('connection-dot').className='dot'+(blocked||state.aiQuotaError?' error':'');
    if(blocked||local){cancelAI();cancelGuidance();}
  }
  if($('d-budget-alert'))$('d-budget-alert').textContent=blocked?'AI unavailable':state.aiQuotaError?'AI tokens unavailable':local?'Local-only mode':'';
}

async function refreshBudget(){D.budget=await dapi('/budget');updateBudgetBadge();renderProfileModelUsage(D.budget);return D.budget;}

async function useProfile(profile){if(state.searchController){state.searchController.abort();state.searchController=null;searchBusy(false);}cancelAI();cancelGuidance();D.suppressSave=true;try{D.profile=profile;const stored=await dapi('/workspace/'+profile.id);D.workspaceRevision=stored.revision;const value=stored.data;D.sensitive=!!value.sensitive;if($("d-sensitive"))$("d-sensitive").checked=D.sensitive;if(D.sensitive)state.prefs.autoGuidance=false;if(value.workspace){state.workspace=value.workspace;}else if(profile.id==='rei'&&stored.revision===0){/* Migrate existing browser work once, preserving the original browser backup. */}else state.workspace={schema_version:SCHEMA,app_version:VERSION,questions:[],constraints:{deadline:'',data:'',mentor:''}};
  for(const field of ['deadline','data','mentor'])$('constraint-'+field).value=state.workspace.constraints?.[field]||'';
  state.prefs.searchReasoning={overall:'medium',specific:'medium'};if(value.prefs)Object.assign(state.prefs,value.prefs);else if(profile.id!=='rei'||stored.revision!==0)state.prefs.sources=profile.sources;
  for(const s of ['pubmed','ensembl','gwas'])$('source-'+s).checked=state.prefs.sources.includes(s);
  if(D.hydrated||!D.startupQueryEdited)$('query').value=D.states.get(profile.id)?.query||'';$('limit').value=state.prefs.limit||10;$('mode').value='auto';
  state.search=D.states.get(profile.id)?.search||null;state.filter='all';state.selected.clear();state.lastAi=null;guidanceCache.clear();$('ai-output').hidden=true;renderSearch();renderSaved();renderRecent();applyProfile();selectTab(D.states.get(profile.id)?.tab||profile.default_tab);updateGuidance();
 }finally{D.suppressSave=false;}syncSearchControls();resizeSearchPrompt();queueWorkspace();}
function applyProfile(){const p=D.profile,u=p.ui;renderIntroduction(p);const nodes={sources_caption:document.querySelector('.source-caption'),welcome_title:$('welcome').querySelector('h2'),welcome_text:$('welcome').querySelector('p'),guidance_heading:$('guidance-card').querySelector('h3'),tip_heading:$('context-tip').querySelector('strong')};for(const [key,node]of Object.entries(nodes)){node.textContent=u[key];decorate(node,p.provenance[key]);}
  $('source-list-label').firstChild.textContent=u.sources_title;decorate($('source-list-label'),p.provenance.sources_title);decorate($('query'),p.provenance.search_placeholder);decorate(document.querySelector('label[for="query"]'),p.provenance.search_label);$('query').placeholder=p.id==='rei'?'e.g. Find research linking BRCA1 variants to breast cancer':u.search_placeholder;document.querySelector('label[for="query"]').textContent=u.search_label==='Research topic, gene, or chromosome region'?'What would you like to discover?':u.search_label;
  if(!state.search)$('results-heading').parentElement.hidden=true;
  $('constraints').querySelector('summary').textContent=u.constraints_heading;decorate($('constraints').querySelector('summary'),p.provenance.constraints_heading);
  for(const [field,key]of [['deadline','deadline'],['data','data'],['mentor','mentor']]){const input=$('constraint-'+field);input.parentNode.firstChild.textContent=u[key+'_label'];input.placeholder=u[key+'_hint'];decorate(input,p.provenance[key+'_hint']);decorate(input.parentNode,p.provenance[key+'_label']);}
  const examples=document.querySelector('.examples');decorate(examples,p.provenance.examples);const label=examples.querySelector('span')?.cloneNode(true)||dnode('span',{text:'Explore:'});examples.replaceChildren(label,...u.examples.map(q=>dbutton(q,()=>{$('query').value=q;return runSearch();},'quiet')));$('welcome').querySelector('button[data-example]').textContent='Explore '+(u.examples[0]||'a topic');$('welcome').querySelector('button[data-example]').dataset.example=u.examples[0]||'research';
  const side=document.querySelector('aside.side');const map={guidance:$('guidance-card'),constraints:$('constraints').closest('.side-card'),tip:$('context-tip')};for(const name of p.panels){map[name].hidden=false;side.append(map[name]);}for(const name of Object.keys(map))if(!p.panels.includes(name))map[name].hidden=true;
  $('d-theme').replaceChildren(dnode('strong',{text:p.name+' · '+(D.levels.find(l=>l.id===p.learning_level)?.name||p.learning_level)}),dnode('small',{text:p.theme_title}),dnode('small',{text:p.goal}));$('d-theme').title=p.name+'\n'+p.theme_title+'\n'+p.goal+'\nSettings';decorate($('d-theme').querySelector('small'),p.provenance.theme_title);renderTabs();}
function workspaceTabs(){const configured=D.profile?.tabs||['evidence'],tabs=configured.filter(name=>!['sources','notes'].includes(name));tabs.splice(Math.max(0,tabs.indexOf('evidence')+1),0,'sources');if(configured.includes('notes'))tabs.push('notes');return tabs;}
function renderTabs(){const bar=$('d-tabs');bar.replaceChildren(...workspaceTabs().map(name=>{const b=dbutton(name==='notes'?'Private documents and Notes':name[0].toUpperCase()+name.slice(1),()=>selectTab(name),'quiet small');b.id='d-tab-'+name;b.setAttribute('role','tab');b.setAttribute('aria-controls',name==='evidence'?'d-evidence':'d-content');b.setAttribute('aria-selected',String(D.tab===name));b.tabIndex=D.tab===name?0:-1;b.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const tabs=workspaceTabs(),i=tabs.indexOf(name),n=tabs.length;const next=e.key==='Home'?0:e.key==='End'?n-1:(i+(e.key==='ArrowRight'?1:-1)+n)%n;selectTab(tabs[next]);$('d-tab-'+tabs[next]).focus();}};return b;}));}
function selectTab(tab){D.tab=workspaceTabs().includes(tab)?tab:(D.profile?.default_tab||'evidence');$('d-evidence').hidden=D.tab!=='evidence';$('d-content').hidden=D.tab==='evidence';renderTabs();if(D.tab!=='evidence'){if(!D.tabBodies)D.tabBodies={};for(const node of $('d-content').children)node.hidden=true;if(D.tabBodies[D.tab])D.tabBodies[D.tab].hidden=false;else{const box=dnode('section',{'aria-label':D.tab});D.tabBodies[D.tab]=box;$('d-content').append(box);if(D.tab==='sources')renderSources(box).catch(e=>toast(e.message));else if(D.tab==='connections')renderConnections(box).catch(e=>toast(e.message));else renderMaterials(box,D.tab).catch(e=>toast(e.message));}}}
function resetTabBodies(){if($('sources-settings'))$('source-strip').append($('sources-settings'));D.tabBodies={};$('d-content').replaceChildren();}

function alignProfileWording(profile){
  const u=profile.ui;
  if(u.eyebrow==='Your fellowship research workspace'&&u.heading==='Find evidence. Shape a question.'&&u.introduction==='Explore a topic, gene, or genomic region. Keep the evidence and the next question together.'){
    u.heading='';u.introduction='Explore topics, genes, or genomic regions to find evidence and shape your next question.';
    profile.provenance.introduction=[profile.provenance.heading,profile.provenance.introduction].find(p=>['ai','ai_edited'].includes(p?.origin))||profile.provenance.introduction;
  }
}
function renderIntroduction(profile,root=document.querySelector('.intro')){
  alignProfileWording(profile);
  const heading=root.querySelector('h1')||$('workspace-title'),description=root.querySelector('p');
  heading.textContent=profile.ui.eyebrow;decorate(heading,profile.provenance.eyebrow);
  const keys=['heading','introduction'].filter(key=>profile.ui[key].trim());
  description.replaceChildren(...keys.map((key,index)=>{
    const span=dnode('span',{text:(index?' ':'')+profile.ui[key]});
    decorate(span,profile.provenance[key]);return span;
  }));
  delete description.dataset.provenance;description.removeAttribute('title');
}

async function profileSettings(){
  let connectionError='';
  if(!HOSTED_DEMO)try{await requiresLocal();}catch(error){connectionError=error.message;}
  const {body,dialog}=drawer('Settings','profile-dialog');D.dirty=false;
  const saved=dnode('section',{class:'d-settings-section','aria-labelledby':'saved-settings-heading'},[
    dnode('h3',{id:'saved-settings-heading',text:'Saved research'}),
    dnode('p',{class:'d-muted',text:state.workspace.questions.length+' saved briefs in this workspace. Review questions, compare briefs, or export a backup.'}),
    dbutton('Open saved research',()=>{dialog.close();setView('saved');$('saved-page').querySelector('h1').focus();})
  ]);
  body.append(saved);
  const library=dbutton('Open local library',async()=>{await requiresLocal();dialog.close();await localLibrary();});library.id='nav-library';library.disabled=!D.ready;
  body.append(dnode('section',{class:'d-settings-section','aria-labelledby':'library-settings-heading'},[
    dnode('h3',{id:'library-settings-heading',text:'Local library'}),
    dnode('p',{class:'d-muted',text:D.ready?'Browse saved activities across profiles, import files, and open or export ZIP archives.':'Run the local application to browse activities and manage ZIP archives.'}),library
  ]));
  if(!D.ready){body.append(dnode('h3',{text:'Profiles'}),dnode('p',{class:'d-muted',text:HOSTED_DEMO?'Run OpenBEXI Discovery locally to use profiles and the library.':connectionError}));return;}
  body.append(dnode('h3',{text:'Profiles'}));
  body.append(dnode('p',{text:'REI is the default. Switch workspaces or create a profile for another learning goal.'}));
  renderProfileUpdateSection(body,dialog);
  for(const p of D.profiles){
    const goal=dnode('p',{text:p.goal});decorate(goal,p.provenance.goal);
    const row=dnode('div',{class:'d-row','data-profile-id':p.id},[dnode('h3',{text:p.name+(p.id===D.profile.id?' · active':'')}),goal,dnode('small',{text:p.learning_level+' · revision '+p.revision})]);
    row.append(dnode('div',{class:'d-bar'},[
      dbutton('Edit',()=>editProfile(clone(p),false)),
      dbutton('Use profile',async()=>{if(p.id===D.profile.id){dialog.close();return;}await D.saveQueue;D.states.set(D.profile.id,{search:state.search,query:$('query').value,tab:D.tab});await dapi('/profiles/action',{id:p.id,revision:p.revision,action:'activate'});resetTabBodies();await useProfile(p);dialog.close();}),
      dbutton(p.id==='rei'?'Reset REI':'Delete',async()=>{if(!confirm(p.id==='rei'?'Reset REI settings? Saved work will remain.':'Delete this profile? Archived work will remain.'))return;await dapi('/profiles/action',{id:p.id,revision:p.revision,action:p.id==='rei'?'reset':'delete'});await reloadProfiles();await useProfile(D.profiles.find(x=>x.id===(p.id===D.profile.id?'rei':D.profile.id)));await profileSettings();},'quiet small d-danger'),
      p.revision>1?dbutton('Roll back profile',async()=>{await rollbackProfile(p);await profileSettings();}):null
    ]));body.append(row);
  }
  body.append(dbutton('Create profile',async()=>editProfile(await dapi('/templates/general'),true),'primary'));
}
async function reloadProfiles(){const data=await dapi('/bootstrap');D.profiles=data.profiles;D.settings=data.settings;D.budget=data.budget;}

async function editProfile(profile,create){alignProfileWording(profile);const {body,dialog}=drawer(create?'Create learning profile':'Edit '+profile.name,'profile-dialog');D.draft=profile;D.dirty=false;body.oninput=()=>D.dirty=true;const status=dnode('div',{class:'d-status',role:'status'});const name=dfield('Profile name',profile.name),goal=dfield('Learning or research goal',profile.goal,'textarea');body.append(name.wrapper,goal.wrapper);
  if(!D.taxonomy)D.taxonomy=(await dapi('/taxonomy')).nodes;
  const themeTitle=dfield('Theme summary',profile.theme_title);body.append(themeTitle.wrapper);
  body.append(buildThemePicker(profile,{open:create,onChange:()=>{D.dirty=true;}}));
  const levels=dnode('details',{open:''},[dnode('summary',{text:'OpenBEXI Discovery — Knowledge Progression'})]);D.levels.forEach((level,i)=>{const input=dnode('input',{type:'radio',name:'learning-level',value:level.id});input.checked=profile.learning_level===level.id;input.onchange=()=>profile.learning_level=level.id;const example=profile.themes.some(id=>id.startsWith('02.01'))?level.example:`${level.description} Apply this to ${profile.theme_title}.`;levels.append(dnode('label',{class:'d-level'},[input,dnode('strong',{text:String(i+1).padStart(2,'0')+' '+level.name}),dnode('small',{text:example})]));});levels.append(dnode('p',{class:'d-muted',text:'Beyond the Frontier represents experimental inquiry, not a guarantee of scientific discovery. AI-generated hypotheses require independent verification.'}));body.append(levels);
  const options=dnode('details',{},[dnode('summary',{text:'Tabs, sources & tools'})]);for(const [key,values]of [['tabs',['evidence','documents','datasets','connections','quizzes','notes']],['sources',['pubmed','ensembl','gwas']],['tools',Object.keys(D.tools)]]){options.append(dnode('h4',{text:key[0].toUpperCase()+key.slice(1)}));for(const value of values){const c=dcheck(value+(key==='tools'&&D.tools[value]!=='available'?' · planned':''),profile[key].includes(value));if(key==='tools'&&D.tools[value]!=='available')c.input.disabled=true;c.input.onchange=()=>{profile[key]=c.input.checked?[...profile[key],value]:profile[key].filter(x=>x!==value);};options.append(c.wrapper);}}const initial=dselect('Initial tab',profile.tabs,profile.default_tab);options.append(initial.wrapper);body.append(options);
  const wording=dnode('details',{},[dnode('summary',{text:'Edit page wording'})]);const fields={};for(const [key,value]of Object.entries(profile.ui)){if(['welcome_heading','guidance_heading','guidance_text','constraints_heading','deadline_label','deadline_hint','data_label','data_hint','mentor_label','mentor_hint','tip_heading','tip_text'].includes(key))continue;const labels={eyebrow:'Workspace heading',heading:'Description lead-in (optional)',introduction:'Workspace description',welcome_title:'Evidence welcome title',welcome_text:'Evidence welcome text'};const f=dfield(labels[key]||key.replaceAll('_',' '),Array.isArray(value)?value.join('\n'):value,Array.isArray(value)||String(value).length>100?'textarea':'text');fields[key]=f.input;f.input.addEventListener('input',()=>{if(['ai','ai_edited'].includes(profile.provenance[key]?.origin))profile.provenance[key].origin='ai_edited';});wording.append(f.wrapper);}body.append(wording);
  const instruction=dfield('Optional AI instructions','Adapt this workspace to my themes, goal, and chosen level.','textarea');const aiDetails=dnode('details',{},[dnode('summary',{text:'AI-assisted wording (optional)'}),instruction.wrapper]);const preview=dnode('div',{class:'d-preview',hidden:''});let reviewed=false;
  function collect(){profile.name=name.input.value.trim();profile.goal=goal.input.value.trim();profile.theme_title=themeTitle.input.value.trim();profile.default_tab=profile.tabs.includes(initial.input.value)?initial.input.value:profile.tabs[0];for(const [key,input]of Object.entries(fields))profile.ui[key]=key==='examples'?input.value.split('\n').map(x=>x.trim()).filter(Boolean):input.value;return profile;}
  aiDetails.append(dbutton('Generate wording draft',async()=>{collect();dstatus(status,'Generating a draft…');const result=await dapi('/ai/draft',{task:create?'create_profile':'update_profile',profile,instruction:instruction.input.value},{timeout:270000});profile=result.profile;D.draft=profile;for(const [key,input]of Object.entries(fields))input.value=Array.isArray(profile.ui[key])?profile.ui[key].join('\n'):profile.ui[key];themeTitle.input.value=profile.theme_title;D.dirty=true;reviewed=false;dstatus(status,result.explanation);await refreshBudget();}));body.append(aiDetails,status,preview);
  function showPreview(){collect();preview.hidden=false;
    const intro=dnode('div',{class:'intro'},[dnode('h1'),' ',dnode('p')]);renderIntroduction(profile,intro);
    const title=dnode('h2',{text:profile.ui.welcome_title}),text=dnode('p',{text:profile.ui.welcome_text});
    decorate(title,profile.provenance.welcome_title);decorate(text,profile.provenance.welcome_text);
    preview.replaceChildren(intro,dnode('div',{class:'d-card'},[title,text]),dnode('p',{text:profile.theme_title+' / '+profile.learning_level}),dnode('p',{text:'Tabs: '+profile.tabs.join(', ')}));reviewed=true;
  }
  body.addEventListener('input',()=>reviewed=false);body.append(dnode('div',{class:'d-bar'},[dbutton('Preview',showPreview),dbutton('Save profile',async()=>{collect();if(!profile.name||!profile.goal||!profile.tabs.length)throw new Error('Provide a name, goal, and at least one tab.');if(!reviewed){showPreview();dstatus(status,'Review the draft above, then select Save profile again.');return;}const original=D.profiles.find(p=>p.id===profile.id);const saved=await dapi('/profiles/save',{profile,base_revision:original?.revision,create});await D.saveQueue;await dapi('/profiles/action',{id:saved.id,revision:saved.revision,action:'activate'});await reloadProfiles();resetTabBodies();await useProfile(saved);D.dirty=false;dialog.close();toast('Profile saved.');},'primary')]));
}

function quizLevelName(level){return D.levels.find(item=>item.id===level)?.name||level;}
async function renderQuizzes(box){
  const profile=clone(D.profile),list=dnode('div'),search=dfield('Search saved quizzes','','search');
  const history=dnode('section',{id:'quiz-history','data-profile':profile.id,'aria-label':'Quiz history'});
  async function load(){const data=await dapi('/library?profile='+profile.id+'&kind=quiz&q='+encodeURIComponent(search.input.value));renderActivityList(list,data.activities);await renderQuizHistory(history,profile.id);}
  box.replaceChildren(dnode('h3',{text:'Quizzes'}),dnode('p',{text:'Start an AI quiz with 8 questions for '+quizLevelName(profile.learning_level)+' · '+profile.theme_title+'. Your score and attempts are saved locally.'}),
    dnode('div',{class:'d-bar'},[dbutton('Start a quiz',()=>startQuiz(load),'primary'),dbutton('Create quiz',()=>materialEditor('quiz')),dbutton('Refresh',load)]),search.wrapper,list,history);
  search.input.oninput=()=>load().catch(error=>toast(error.message));await load();
}
async function startQuiz(refresh=async()=>{}){
  await requiresLocal();await refreshBudget();
  if(!state.health?.ai.configured||D.settings.local_only||D.budget?.blocked){openAISetup();return;}
  const profile=clone(D.profile),sensitive=!!D.sensitive;
  const payload={task:'create_quiz',profile,instruction:'Create exactly 8 multiple-choice questions for my current learning goal and level.',sensitive,consent_ai:false};
  if(sensitive){payload.consent_ai=await reviewSensitiveRequest(payload);if(!payload.consent_ai||!confirm('Save the generated quiz containing sensitive material on this computer?'))return;}
  const {body,dialog}=drawer('Start a quiz','quiz-start-dialog'),controller=new AbortController();
  dialog.addEventListener('close',()=>controller.abort(),{once:true});
  const status=dnode('p',{class:'d-status',role:'status',text:'Creating 8 questions for '+quizLevelName(profile.learning_level)+'…'});
  body.append(dnode('p',{text:profile.theme_title+' · '+profile.goal}),status,dbutton('Cancel',()=>dialog.close()));
  try{
    const result=await dapi('/ai/draft',payload,{timeout:270000,signal:controller.signal});if(controller.signal.aborted)return;
    dstatus(status,'Saving your quiz…');
    const item=await dapi('/library',{profile_id:profile.id,kind:'quiz',title:result.title,payload:{title:result.title,questions:result.questions},provenance:result.provenance,request:payload.instruction,sensitive,consent_local:sensitive},{signal:controller.signal});
    if(controller.signal.aborted)return;dialog.close();await refresh().catch(error=>toast(error.message));await openActivity(item.id);
  }catch(error){if(controller.signal.aborted)return;dstatus(status,error.message,true);body.append(dbutton('Try again',()=>{dialog.close();return startQuiz(refresh);}));}
}
async function renderQuizHistory(box,profileId){
  const {attempts}=await dapi('/quiz/history?profile_id='+encodeURIComponent(profileId));
  box.replaceChildren(dnode('h3',{text:'Quiz history'}));
  if(!attempts.length){box.append(dnode('p',{class:'d-muted',text:'No quiz attempts yet. Complete a quiz to see your score here.'}));return;}
  box.append(dbutton('Clear history',async()=>{
    if(!confirm('Remove all quiz attempts for this profile from this computer? Saved quizzes will remain.'))return;
    await dapi('/quiz/history/delete',{profile_id:profileId});await renderQuizHistory(box,profileId);
  },'quiet small d-danger'));
  for(const item of attempts){
    const row=dnode('article',{class:'d-row d-quiz-attempt'},[dnode('h4',{text:item.title}),
      dnode('p',{text:`Score: ${item.score} / ${item.total} · ${Math.round(item.score/item.total*1000)/10}% · ${quizLevelName(item.learning_level)}`}),
      dnode('small',{class:'d-muted',text:new Date(item.created_at).toLocaleString()})]);
    row.append(dnode('div',{class:'d-bar'},[dbutton('Review attempt',()=>openActivity(item.id)),dbutton('Remove attempt',async()=>{
      if(!confirm('Remove this quiz attempt from history? The saved quiz will remain.'))return;
      await dapi('/quiz/history/delete',{profile_id:profileId,attempt_id:item.id});await renderQuizHistory(box,profileId);
    },'quiet small d-danger')]));box.append(row);
  }
}
async function refreshQuizHistory(){const box=$('quiz-history');if(box)await renderQuizHistory(box,box.dataset.profile);}
function renderQuizAttempt(body,item){
  const result=item.payload,review=dnode('div',{class:'d-quiz-result',tabindex:'-1',role:'status'},[
    dnode('h3',{text:`Score: ${result.score} / ${result.total}`}),dnode('p',{text:`${Math.round(result.score/result.total*1000)/10}% correct · ${quizLevelName(result.quiz_level||item.learning_level)}`})]);
  if(result.quiz_provenance)review.append(dnode('small',{class:'d-origin',text:'Quiz: '+originLabel({provenance:result.quiz_provenance})}));
  for(const [index,question]of (result.questions||[]).entries()){
    const correct=result.answers[index]===question.answer;
    review.append(dnode('section',{class:'d-quiz-feedback '+(['ai','ai_edited'].includes(result.quiz_provenance?.origin)?'d-ai':'d-source')},[dnode('h4',{text:(index+1)+'. '+question.question}),
      dnode('p',{text:'Your answer: '+question.choices[result.answers[index]]+' · '+(correct?'Correct':'Incorrect')}),
      dnode('p',{text:'Correct answer: '+question.choices[question.answer]}),dnode('p',{text:question.explanation})]));
  }
  body.append(review);return review;
}
function renderQuizQuestions(body,item,archive){
  const quiz=item.payload,answers=Array(quiz.questions.length).fill(null),form=dnode('form',{class:'d-quiz-form'});let submitted=false;
  form.addEventListener('submit',event=>event.preventDefault());
  for(const [index,question]of quiz.questions.entries()){
    const field=dnode('fieldset',{class:'d-quiz-question '+(['ai','ai_edited'].includes(item.provenance?.origin)?'d-ai':'')},[dnode('legend',{text:(index+1)+'. '+question.question})]);
    for(const [choiceIndex,choice]of question.choices.entries()){
      const radio=dnode('input',{type:'radio',name:'quiz-'+index,value:choiceIndex,required:''});radio.onchange=()=>answers[index]=choiceIndex;
      field.append(dnode('label',{class:'d-check'},[radio,choice]));
    }form.append(field);
  }
  body.append(form);
  if(!archive){
    const submit=dbutton('Grade & save attempt',async()=>{
      if(submitted||!form.reportValidity())return;
      const result=await dapi('/quiz/attempt',{activity_id:item.id,answers,profile_id:item.profile_id});submitted=true;
      const resultArea=dnode('div');form.replaceWith(resultArea);
      const review=renderQuizAttempt(resultArea,result);review.focus({preventScroll:true});resultArea.append(dbutton('Take quiz again',()=>openActivity(item.id)));
      body.closest('dialog').scrollTop=0;
      await refreshQuizHistory();
    },'primary');form.append(submit);
  }
}
async function refreshLibraryViews(){
  resetTabBodies();selectTab(D.tab);
  if($('library-dialog')?.open&&D.libraryRefresh)await D.libraryRefresh();
}
async function documentEditor(existing=null,importFile=false){
  const profileId=existing?.profile_id||D.profile.id;
  const {body,dialog}=drawer(existing?'Edit document':importFile?'Import document':'New document','material-dialog');
  const title=dfield('Title',existing?.title||''),content=dfield('Content / notes',existing?.content||'','textarea');
  const originalText=content.input.value;
  title.input.maxLength=240;content.input.maxLength=250000;content.input.rows=12;
  content.input.readOnly=!!existing?.content_truncated;
  const file=dnode('input',{type:'file',accept:'.pdf,.md,.txt,.json'});
  const hint=dnode('p',{class:'d-muted'}),status=dnode('div',{class:'d-status',role:'status'});
  const sensitive=dcheck('Contains sensitive information',existing?.sensitive||false);
  sensitive.input.disabled=!!existing?.sensitive;
  const consent=dcheck('I authorize saving this sensitive material on this computer',false);
  let fileError='',selectedText=false,selection=0;
  function describeFile(){hint.textContent=content.input.readOnly
    ?'This file exceeds the 250,000-character editor limit. You can change its title or upload a replacement; the complete file is retained.'
    :'Write document text here, or choose a UTF-8 text file. For a PDF, use this field for notes and upload a replacement to change its pages.';}
  describeFile();
  body.append(title.wrapper,dnode('label',{},[existing?'Replace file (optional; up to 8 MB)':'File (optional; up to 8 MB)',file]));
  if(existing?.filename)body.append(dnode('p',{class:'d-muted',text:'Attached: '+(existing.original_filename||existing.filename)+'. Leave the file picker empty to keep it.'}));
  body.append(content.wrapper,hint,sensitive.wrapper,consent.wrapper,status);
  const save=dbutton(existing?'Save changes':'Save locally',async()=>{
    try{
      if(fileError)throw new Error(fileError);
      const chosen=file.files[0],name=title.input.value.trim()||chosen?.name;
      if(!name)throw new Error('Enter a document title.');
      const value={title:name,content:existing&&!chosen&&content.input.value===originalText?existing.content:content.input.value,
        sensitive:sensitive.input.checked,consent_local:consent.input.checked};
      if(chosen){
        value.filename=chosen.name;
        value.file_base64=await dbase64(selectedText&&!content.input.readOnly?new Blob([content.input.value]):chosen);
      }
      dstatus(status,'Saving document…');
      const saved=existing?await dapi('/library/'+existing.id+'/update',{...value,base_revision:existing.revision||1})
        :await dapi('/library',{...value,profile_id:profileId,kind:'document'});
      dialog.close();await refreshLibraryViews();await openActivity(saved.id);
      toast(existing?'Document updated.':'Document saved to local library.');
    }catch(error){dstatus(status,error.message,true);}
  },'primary');
  file.onchange=async()=>{
    const currentSelection=++selection,chosen=file.files[0];
    save.disabled=true;fileError='';selectedText=false;dstatus(status,'');
    try{
      if(chosen){
        if(chosen.size>8*1024*1024)throw new Error('Choose a file no larger than 8 MB.');
        if(!/\.(pdf|md|txt|json)$/i.test(chosen.name))throw new Error('Choose a PDF, Markdown, text, or JSON file.');
        if(!/\.pdf$/i.test(chosen.name)){
          const text=new TextDecoder('utf-8',{fatal:true}).decode(await chosen.arrayBuffer());
          if(currentSelection!==selection)return;
          selectedText=true;content.input.value=text.slice(0,250000);content.input.readOnly=text.length>250000;
        }else{content.input.readOnly=false;content.input.value=existing?.filename?.endsWith('.pdf')?existing.content:'';}
        if(!title.input.value.trim())title.input.value=chosen.name.slice(0,240);
      }else{content.input.value=existing?.content||'';content.input.readOnly=!!existing?.content_truncated;}
    }catch(error){if(currentSelection!==selection)return;fileError=error instanceof TypeError?'Text files must use UTF-8 encoding.':error.message;dstatus(status,fileError,true);}
    finally{if(currentSelection===selection){save.disabled=!!fileError;describeFile();}}
  };
  body.append(dnode('div',{class:'d-bar'},[save,dbutton('Cancel',()=>dialog.close())]));
}
async function renderMaterials(box,tab){if(tab==='quizzes')return renderQuizzes(box);const kind={documents:'document',datasets:'dataset',notes:'note'}[tab];box.replaceChildren(dnode('h3',{text:tab==='notes'?'Private documents and Notes':tab[0].toUpperCase()+tab.slice(1)}));const list=dnode('div'),q=dfield('Search saved material','','search');const bar=dnode('div',{class:'d-bar'},[dbutton('Refresh',load),dbutton(tab==='documents'?'New document':tab==='notes'?'New note':'Import file',()=>kind==='document'?documentEditor():materialEditor(kind)),...(tab==='documents'?[dbutton('Import file',()=>documentEditor(null,true))]:[])]);box.append(bar,q.wrapper,list);q.input.oninput=()=>load();async function load(){const data=await dapi('/library?profile='+D.profile.id+'&kind='+kind+'&q='+encodeURIComponent(q.input.value));renderActivityList(list,data.activities);}await load();}
function renderActivityList(box,items,archive=null){
  box.replaceChildren();
  if(!items.length)box.append(dnode('p',{class:'d-muted',text:'No saved material yet. Import a file or create an activity.'}));
  for(const item of items){
    const info=dnode('div',{class:'d-item-info'},[dnode('h3',{text:item.title}),
      dnode('p',{class:'d-item-summary',text:item.summary||String(item.content||'Saved '+item.kind).replace(/\s+/g,' ').slice(0,180)}),
      dnode('small',{text:`${item.kind} · ${formatDate(item.created_at)} · ${item.learning_level}${item.sensitive?' · sensitive':''}`}),
      dnode('small',{class:'d-origin',text:originLabel(item)})]);
    const actions=dnode('div',{class:'d-item-actions'});
    if(!archive&&item.kind==='quiz')actions.append(dbutton('Start',()=>openActivity(item.id),'primary small'));
    if(!archive&&['document','dataset','note','quiz','attempt','search','ai'].includes(item.kind)){
      actions.append(dbutton('Summarize',()=>materialAI(item.id,item.kind,'summarize')),dbutton('Analyze with AI',()=>materialAI(item.id,item.kind,'analyze')));
    }
    if(archive||item.kind!=='quiz')actions.append(dbutton('Open',()=>openActivity(item.id,archive)));
    if(!archive){
      if(item.kind==='document')actions.append(dbutton('Edit',async()=>documentEditor(await dapi('/library/'+item.id))));
      else if(item.kind==='dataset')actions.append(dbutton('Edit',async()=>privacyReview(await dapi('/datasets/'+item.id+'/review',{}))));
      else if(['note','quiz'].includes(item.kind)&&item.profile_id===D.profile.id)actions.append(dbutton('Edit',async()=>materialEditor(item.kind,await dapi('/library/'+item.id))));
      const remove=dbutton(item.kind==='quiz'?'Delete quiz':'Delete',()=>deleteMaterial(item.id,item.kind),'quiet small d-danger');remove.dataset.caption=item.kind==='quiz'?'Delete this saved quiz after confirmation. Previous attempts and scores remain.':'Delete this local activity and its attached file after confirmation. ZIP backups remain.';actions.append(remove);
    }
    box.append(dnode('article',{class:'d-row d-item-row '+(['ai','ai_edited'].includes(item.provenance?.origin)?'d-ai':'d-source'),'data-activity-id':item.id},[info,actions]));
  }
}
async function deleteMaterial(id,kind=null){
  if(!confirm(kind==='quiz'?'Delete this saved quiz? Previous attempts, scores, and ZIP backups will remain.':'Permanently delete this activity and its attached file? Existing ZIP backups will remain.'))return;
  await dapi('/library/'+id+'/delete',{});
  if($('activity-dialog')?.dataset.activityId===id)$('activity-dialog').close();
  await refreshLibraryViews();toast('Local activity deleted.');
}
async function materialAI(id,kind,action){
  const label=action==='summarize'?'Summarize':'Analyze with AI';
  const {body,dialog}=drawer(label+' · '+kind,'material-ai-dialog');
  if(kind==='dataset'){await datasetAnalysisPanel(body,id,action==='summarize'?'Summarize this reviewed dataset and its main limitations.':'Analyze patterns, comparisons, and limitations in this reviewed dataset.');return;}
  const status=dnode('p',{class:'d-status',role:'status',text:'Loading saved text…'});body.append(status);
  try{
    const context=await dapi('/library/'+id+'/ai-context');if(!dialog.open)return;
    const question=dfield('Focus (optional)','','textarea'),consent=dcheck('Send the reviewed text to the connected AI',false),output=dnode('div',{class:'d-analysis-output',tabindex:'-1'});
    question.input.rows=2;question.input.maxLength=4000;
    body.prepend(dnode('h3',{text:context.title}),dnode('p',{class:'d-muted',text:context.scope}),
      dnode('details',{},[dnode('summary',{text:'Review text sent to AI'}),dnode('pre',{text:context.text})]),question.wrapper,consent.wrapper);
    body.append(dbutton(action==='summarize'?'Summarize with AI':'Analyze with AI',async()=>{
      if(!consent.input.checked){dstatus(status,'Review the text and authorize sending it to AI.',true);return;}
      if(!state.health?.ai.configured){openAISetup();return;}
      const controller=new AbortController();D.aiControllers.add(controller);
      const cancel=()=>controller.abort();dialog.addEventListener('close',cancel,{once:true});
      dstatus(status,'Working…');
      try{
        const result=await dapi('/library/'+id+'/analyze',{action,question:question.input.value,context_hash:context.context_hash,consent_ai:true},{timeout:270000,signal:controller.signal});
        if(!dialog.open)return;
        output.replaceChildren(dnode('article',{class:'d-ai d-analysis-answer'},[dnode('small',{class:'d-origin',text:originLabel(result)}),dnode('p',{text:result.text}),dnode('small',{text:result.scope})]));
        dstatus(status,'Ready.');output.focus({preventScroll:true});output.scrollIntoView({block:'nearest'});
      }catch(error){dstatus(status,error.message,true);}
      finally{D.aiControllers.delete(controller);dialog.removeEventListener('close',cancel);}
    },'primary'),output);dstatus(status,'');
  }catch(error){dstatus(status,error.message,true);}
}
async function materialEditor(kind,existing=null){const {body,dialog}=drawer(existing?'Revise saved '+kind:'New '+kind,'material-dialog');const title=dfield('Title',existing?.title||''),content=dfield(kind==='quiz'?'Quiz JSON (questions, choices, zero-based answer, explanation)':'Content / notes',existing?.content||'','textarea');content.input.rows=8;const sensitive=dcheck('Contains sensitive information',existing?.sensitive||false),consent=dcheck('I authorize saving this sensitive material on this computer',false);let provenance=existing?.provenance||{origin:'user'};body.append(title.wrapper);let file=null;if(['document','dataset'].includes(kind)){file=dnode('input',{type:'file',accept:kind==='dataset'?'.csv,.json':'.pdf,.md,.txt,.json'});body.append(dnode('label',{},['File (up to 8 MB; UTF-8 for text)',file]));}if(kind==='quiz')content.input.value=existing?JSON.stringify(existing.payload,null,2):JSON.stringify({title:'Evidence basics',questions:[{question:'What should accompany a research claim?',choices:['A traceable source','A confident tone'],answer:0,explanation:'Sources make a claim reviewable.'}]},null,2);body.append(content.wrapper,sensitive.wrapper,consent.wrapper);const status=dnode('div',{class:'d-status',role:'status'});if(kind==='quiz'){const instruction=dfield('Optional AI quiz request','Create an 8-question quiz for my learning goal and level.','textarea');body.append(instruction.wrapper,dbutton('Generate quiz with AI',async()=>{dstatus(status,'Generating quiz…');const result=await dapi('/ai/draft',{task:'create_quiz',profile:D.profile,instruction:instruction.input.value,sensitive:sensitive.input.checked,consent_ai:sensitive.input.checked?confirm('Send this exact quiz request to the configured AI model?'):false},{timeout:270000});provenance=result.provenance;content.input.value=JSON.stringify({title:result.title,questions:result.questions},null,2);title.input.value=result.title;content.input.classList.add('d-ai');dstatus(status,'Review the generated quiz before saving.');await refreshBudget();}));}body.append(status,dbutton('Save locally',async()=>{let payload=existing?.payload||{};if(kind==='quiz')payload=JSON.parse(content.input.value);const chosen=file?.files[0];const saved=await dapi('/library',{profile_id:D.profile.id,kind,title:title.input.value||chosen?.name||'Untitled '+kind,content:kind==='quiz'?'':content.input.value,payload,sensitive:sensitive.input.checked,consent_local:consent.input.checked,parent_id:existing?.id||null,provenance,filename:chosen?.name||'',file_base64:chosen?await dbase64(chosen):''});dialog.close();toast('Saved to local library.');resetTabBodies();selectTab(D.tab);return saved;},'primary'));}
async function openActivity(id,archive=null){const item=archive?archive.activities.find(a=>a.id===id):await dapi('/library/'+id);const {body,dialog}=drawer(item.title,'activity-dialog');dialog.dataset.activityId=id;body.append(dnode('small',{class:'d-origin',text:originLabel(item)}),dnode('p',{class:'d-muted',text:item.created_at+' · '+item.profile_snapshot.name+' · '+item.learning_level}));if(archive)body.append(dnode('p',{class:'notice',text:'Read-only ZIP. Import this archive before editing or recording new results.'}));const source=archive?endpoint('/api/discovery/archives/'+archive.id+'/file?path='+encodeURIComponent('profiles/'+item.profile_id+'/activities/'+item.id+'/'+item.filename)):endpoint('/api/discovery/library/'+id+'/file');if(item.filename?.endsWith('.pdf'))body.append(dnode('iframe',{class:'d-pdf',src:source,title:item.title}));if(item.content)body.append(dnode('div',{class:'d-document '+(['ai','ai_edited'].includes(item.provenance?.origin)?'d-ai':'d-source'),text:item.content}));
  if(item.kind==='document'){
    if(item.updated_at)body.append(dnode('p',{class:'d-muted',text:'Updated '+formatDate(item.updated_at)+' · revision '+item.revision}));
    if(item.content_truncated)body.append(dnode('p',{class:'notice',text:'Showing the first 250,000 characters. Download the file to read the full document.'}));
    if(item.filename)body.append(dbutton('Download document file',async()=>{const response=await fetchBounded(source);downloadBlob(item.original_filename||item.filename,await response.blob());}));
  }
  if(item.request)body.append(dnode('h3',{text:'Original request'}),dnode('pre',{text:item.request}),dbutton('Copy request to search draft',()=>{$('query').value=item.request.slice(0,250);toast('Request copied. It has not been sent.');}));if(item.prompts?.length){const details=dnode('details',{},[dnode('summary',{text:'Composed prompt and template context'}),dnode('pre',{text:JSON.stringify(item.prompts,null,2)})]);body.append(details);}
  if(item.kind==='quiz')renderQuizQuestions(body,item,archive);
  else if(item.kind==='attempt')renderQuizAttempt(body,item);
  else if(item.kind==='dataset'&&!archive){const rows=dnode('div');let offset=0;const filter=dfield('Filter saved rows','','search');async function load(){const result=await dapi('/library/'+id+'/rows?offset='+offset+'&q='+encodeURIComponent(filter.input.value));renderTable(rows,result.rows);caption.textContent=`${result.total} rows · snapshot ${formatDate(result.captured_at)} · page ${Math.floor(offset/50)+1}`;}const caption=dnode('p',{class:'d-muted'});filter.input.onchange=()=>{offset=0;load().catch(e=>toast(e.message));};body.append(filter.wrapper,caption,rows,dnode('div',{class:'d-bar'},[dbutton('Previous',()=>{offset=Math.max(0,offset-50);return load();}),dbutton('Next',()=>{offset+=50;return load();})]));await load();}
  else if(Object.keys(item.payload||{}).length)body.append(dnode('pre',{class:['ai','ai_edited'].includes(item.provenance?.origin)?'d-ai':'',text:JSON.stringify(item.payload,null,2)}));
  if(!archive){const actions=dnode('div',{class:'d-bar'});actions.append(dbutton('Restore as a new profile',async()=>{if(!confirm('Create a separate profile from this historical snapshot? Current profiles will be preserved.'))return;const created=await dapi('/library/'+id+'/restore-profile',{consent_sensitive:!!item.sensitive});await reloadProfiles();toast('Created '+created.name+'. Select it in Profile settings.');}));if(item.kind==='document')actions.append(dbutton('Edit document',()=>documentEditor(item)));if(['note','quiz'].includes(item.kind)&&D.profile.id===item.profile_id)actions.append(dbutton('Save a revised copy',()=>materialEditor(item.kind,item)));actions.append(dbutton('Export this activity',()=>exportArchive({activity_id:id},item.sensitive)),dbutton('Delete local activity',async()=>{await deleteMaterial(id);},'quiet small d-danger'));body.append(actions);}}
function renderTable(box,rows){box.replaceChildren();if(!rows.length){box.append(dnode('p',{text:'No rows matched.'}));return;}const columns=Object.keys(rows[0]);const table=dnode('table',{class:'d-table'},[dnode('thead',{},dnode('tr',{},columns.map(k=>dnode('th',{text:k})))),dnode('tbody',{},rows.map(row=>dnode('tr',{},columns.map(k=>dnode('td',{text:asText(row[k],'')})))))]);box.append(dnode('div',{class:'d-table-wrap'},table));}

async function localLibrary(){await requiresLocal();const {body}=drawer('Local library','library-dialog');const q=dfield('Search text and metadata','','search'),profile=dselect('Profile',[['','All profiles'],...D.profiles.map(p=>[p.id,p.name])],''),kind=dselect('Content type',['','document','dataset','note','quiz','attempt','search','ai','workspace'],''),level=dselect('Level',[['','All levels'],...D.levels.map(l=>[l.id,l.name])],''),after=dfield('From date','','date'),before=dfield('Through date','','date');const list=dnode('div');body.append(dnode('p',{text:'Saved work stays on this computer. ZIP archives can be opened without AI and imported as historical copies.'}),dnode('div',{class:'d-bar'},[dbutton('Export current profile',()=>exportArchive({profile_id:D.profile.id})),dbutton('Export entire library',()=>exportArchive({})),dbutton('Open ZIP',()=>openArchivePicker())]),q.wrapper,dnode('div',{class:'d-grid'},[profile.wrapper,kind.wrapper,level.wrapper,after.wrapper,before.wrapper]),list);async function load(){const params=new URLSearchParams({q:q.input.value,profile:profile.input.value,kind:kind.input.value,level:level.input.value,after:after.input.value,before:before.input.value});renderActivityList(list,(await dapi('/library?'+params)).activities);}D.libraryRefresh=load;for(const f of [q,profile,kind,level,after,before])f.input.onchange=()=>load().catch(e=>toast(e.message));await load();}
async function exportArchive(selection,sensitive=false){await D.saveQueue;const {body,dialog}=drawer('Review ZIP export','export-dialog');const params=new URLSearchParams({profile:selection.profile_id||''});const all=(await dapi('/library?'+params)).activities.filter(x=>!selection.activity_id||x.id===selection.activity_id);if(!selection.activity_id){for(const p of D.profiles.filter(p=>!selection.profile_id||p.id===selection.profile_id)){const w=await dapi('/workspace/'+p.id);all.push({id:p.id,title:p.name+' — current profile and workspace backup',sensitive:!!w.data.sensitive});}}body.append(dnode('p',{text:`Export ${all.length} selected activities/backups. Credentials and live connection settings are excluded.`}));const sensitiveItems=all.filter(x=>x.sensitive);const include=dcheck('Include the sensitive local snapshots listed below',false);if(sensitiveItems.length){body.append(include.wrapper,...sensitiveItems.map(x=>dnode('p',{text:x.title+' · '+x.id})));}body.append(dbutton('Download ZIP',async()=>{const response=await dapi('/archives/export',{...selection,include_sensitive:include.input.checked},{raw:true});const blob=await response.blob();downloadBlob('OpenBEXI-Discovery-1.1.zip',blob);dialog.close();},'primary'));}
function downloadBlob(name,blob){const url=URL.createObjectURL(blob),a=dnode('a',{href:url,download:name});document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function openArchivePicker(){const input=dnode('input',{type:'file',accept:'.zip'});input.onchange=async()=>{try{const archive=await dapi('/archives/open',{file_base64:await dbase64(input.files[0])},{timeout:45000});D.archive=archive;const {body}=drawer('ZIP archive · read-only','archive-dialog');const q=dfield('Search archive','','search'),list=dnode('div');const consent=dcheck('I authorize local retention of the sensitive items in this archive',false);body.append(q.wrapper,list,consent.wrapper,dbutton('Import reviewed archive',async()=>{const result=await dapi('/archives/import',{id:archive.id,consent_sensitive:consent.input.checked},{timeout:45000});toast(`${result.imported.length} imported; ${result.skipped} identical items skipped. Profiles were not overwritten.`);resetTabBodies();selectTab(D.tab);},'primary'));q.input.oninput=()=>renderActivityList(list,archive.activities.filter(x=>JSON.stringify(x).toLowerCase().includes(q.input.value.toLowerCase())),archive);renderActivityList(list,archive.activities,archive);}catch(error){toast(error.message);}};input.click();}

async function renderConnections(box){box.replaceChildren(dnode('h3',{text:'Connections'}),dnode('p',{class:'d-muted',text:'SQLite · read-only, on this computer. Account-provider integrations are planned. No data is sent to AI when browsing.'}));const list=dnode('div');box.append(dbutton('Connect SQLite database',()=>connectionForm()),list);const data=await dapi('/connections');for(const item of data.connections){list.append(dnode('div',{class:'d-row'},[dnode('h3',{text:item.name}),dnode('p',{text:item.storage+' · '+(item.sensitive?'sensitive':'non-sensitive')+' · read-only'}),dnode('div',{class:'d-bar'},[dbutton('Browse tables',()=>databaseBrowser(item)),dbutton('Disconnect',async()=>{if(confirm('Disconnect this source? Local library snapshots will remain.')){await dapi('/connections/'+item.id+'/disconnect',{});await renderConnections(box);}},'quiet small d-danger')])]));}if(!data.connections.length)list.append(dnode('p',{text:'Connect a local SQLite file or upload a copy. Python and SQLite are included in the Windows app.'}));}
function connectionForm(){const returnTab=D.tab==='sources'?'sources':'connections';const {body,dialog}=drawer('Connect SQLite','connect-dialog');const name=dfield('Connection name','Research dataset'),path=dfield('Existing database path on this computer (optional)',''),file=dnode('input',{type:'file',accept:'.sqlite,.sqlite3,.db'}),sensitive=dcheck('Contains sensitive data',true),consent=dcheck('I authorize retaining an uploaded database copy locally',false);body.append(name.wrapper,path.wrapper,dnode('label',{},['Or upload a SQLite copy (up to 8 MB)',file]),sensitive.wrapper,consent.wrapper,dnode('p',{class:'d-muted',text:'Uploaded databases stay in private application storage. Queries select named columns only; SQL writes are not supported.'}),dbutton('Connect read-only',async()=>{await dapi('/connections',{profile_id:D.profile.id,name:name.input.value,path:path.input.value,file_base64:file.files[0]?await dbase64(file.files[0]):'',sensitive:sensitive.input.checked,consent_local:consent.input.checked});dialog.close();resetTabBodies();selectTab(returnTab);window.dispatchEvent(new Event('discovery-sources-changed'));},'primary'));}
function databaseBrowser(connection){const {body}=drawer(connection.name,'database-dialog');const table=dselect('Table',Object.keys(connection.tables),Object.keys(connection.tables)[0]),fields=dnode('div',{class:'d-grid'}),filterField=dselect('Filter column (optional)',['',...(connection.tables[table.input.value]||[])],''),filterValue=dfield('Equals',''),rows=dnode('div'),caption=dnode('p',{class:'d-muted'});let offset=0,selected=[];function choose(){fields.replaceChildren();selected=[];for(const name of connection.tables[table.input.value]||[]){const field=dcheck(name,false);field.input.onchange=()=>selected=field.input.checked?[...selected,name]:selected.filter(x=>x!==name);fields.append(field.wrapper);}filterField.input.replaceChildren(...['',...(connection.tables[table.input.value]||[])].map(x=>dnode('option',{text:x,value:x})));offset=0;rows.replaceChildren();}table.input.onchange=choose;choose();function payload(snapshot=false){return {connection_id:connection.id,table:table.input.value,fields:selected,filters:filterField.input.value?{[filterField.input.value]:filterValue.input.value}:{},offset,profile_id:D.profile.id,snapshot,consent_local:false};}async function load(){const data=await dapi('/connections/query',payload());renderTable(rows,data.rows);caption.textContent=`Live read-only preview · ${data.rows.length} rows · offset ${offset} · ${data.captured_at}`;}
  body.append(dnode('p',{text:'Select only the fields needed for this task. Previewing does not save records or send them to AI.'}),table.wrapper,fields,filterField.wrapper,filterValue.wrapper,dnode('div',{class:'d-bar'},[dbutton('Preview selected fields',()=>{offset=0;return load();}),dbutton('Previous',()=>{offset=Math.max(0,offset-50);return load();}),dbutton('Next',()=>{offset+=50;return load();})]),caption,rows,dbutton('Save this page as offline snapshot',async()=>{const p=payload(true);p.consent_local=confirm(`Save up to 50 rows from ${p.table}, fields: ${selected.join(', ')} locally? ${connection.sensitive?'This contains sensitive data.':''}`);if(!p.consent_local)return;await dapi('/connections/query',p);toast('Snapshot saved in Datasets.');resetTabBodies();selectTab(D.tab);}));}

function renderProfileModelUsage(usage){
  const box=$('ai-usage-table');if(!box)return;
  if(!usage.breakdown.length){box.replaceChildren(dnode('p',{class:'d-muted',text:'No AI requests recorded yet.'}));return;}
  renderTable(box,usage.breakdown.map(row=>({
    Profile:D.profiles.find(profile=>profile.id===row.profile)?.name||row.profile,
    Model:row.model,Requests:row.requests,Tokens:row.tokens.toLocaleString(),
    'Estimated USD':row.unknown_cost?'Unknown':'$'+row.estimated_usd.toFixed(4)
  })));
}
async function renderAISettingsDetails(){
  const body=$('ai-discovery-settings');body.hidden=false;body.replaceChildren(dnode('p',{class:'d-muted',text:'Loading local AI settings…'}));
  try{await requiresLocal();}catch(error){body.replaceChildren(dnode('p',{class:'d-muted',text:'Local settings unavailable. '+error.message}));return;}
  const usage=await refreshBudget(),local=dcheck('Local-only mode — no external requests',D.settings.local_only);
  local.input.onchange=async()=>{
    local.input.disabled=true;
    try{D.settings=await dapi('/settings',{local_only:local.input.checked});D.lastBudgetError='';updateBudgetBadge();if(!D.settings.local_only&&!D.budget.blocked)await checkHealth();renderAISetup();}
    catch(error){local.input.checked=D.settings.local_only;toast(error.message);}
    finally{local.input.disabled=false;}
  };
  body.replaceChildren(local.wrapper);
  if(usage.blocked&&(usage.config.token_limit!==null||usage.config.cost_limit!==null)){
    body.append(dbutton('Remove saved local limits',async()=>{D.budget=await dapi('/budget',{period:usage.config.period,token_limit:null,cost_limit:null});D.lastBudgetError='';updateBudgetBadge();await renderAISettingsDetails();if(!D.settings.local_only)await checkHealth();renderAISetup();}));
  }
  body.append(dnode('h3',{text:'By profile and model'}),dnode('div',{id:'ai-usage-table'}),
    dnode('p',{class:'d-muted',text:'Requests from this installation in the current accounting period, including pending requests. Costs are estimates; OpenAI does not report your remaining account credits here.'}));
  renderProfileModelUsage(usage);
}

function launchDefaultSearch(){
  if(D.launchSearchStarted)return;
  D.launchSearchStarted=true;
  if(!D.ready||D.profile?.id!=='rei'||D.settings.local_only||D.sensitive||D.startupQueryEdited||state.searchController||state.search||$('query').value.trim()||!selectedSources().length)return;
  runSearch(DEFAULT_QUERY,'specific',{automatic:true}).catch(error=>toast(error.message));
}
function settingsIcon(){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),path=document.createElementNS(svg.namespaceURI,'path');
  svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('class','d-settings-icon');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');
  path.setAttribute('fill','currentColor');path.setAttribute('fill-rule','evenodd');path.setAttribute('d','M8.82 4.33L9.85 3.98L9.26 1.76L14.74 1.76L14.15 3.98L15.18 4.33L15.18 4.33L16.15 4.81L17.30 2.82L21.18 6.70L19.19 7.85L19.67 8.82L19.67 8.82L20.02 9.85L22.24 9.26L22.24 14.74L20.02 14.15L19.67 15.18L19.67 15.18L19.19 16.15L21.18 17.30L17.30 21.18L16.15 19.19L15.18 19.67L15.18 19.67L14.15 20.02L14.74 22.24L9.26 22.24L9.85 20.02L8.82 19.67L8.82 19.67L7.85 19.19L6.70 21.18L2.82 17.30L4.81 16.15L4.33 15.18L4.33 15.18L3.98 14.15L1.76 14.74L1.76 9.26L3.98 9.85L4.33 8.82L4.33 8.82L4.81 7.85L2.82 6.70L6.70 2.82L7.85 4.81L8.82 4.33Z M16.5 12A4.5 4.5 0 1 0 7.5 12A4.5 4.5 0 1 0 16.5 12Z');
  svg.append(path);return svg;
}
async function initDiscovery(){
  $('d-sensitive').onchange=()=>{D.sensitive=$('d-sensitive').checked;D.sensitiveConsent=false;if(D.sensitive){state.prefs.autoGuidance=false;cancelGuidance();}queueWorkspace();updateGuidance();};
  $('query').addEventListener('input',()=>{if(!D.hydrated)D.startupQueryEdited=true;});
  const legend=$('content-provenance');document.querySelector('.site-header').after(legend);legend.querySelector('.d-legend-detail').hidden=true;
  const gear=dbutton('',()=>profileSettings(),'quiet small d-gear');gear.append(settingsIcon());gear.id='profile-settings';gear.title='Settings';gear.setAttribute('aria-label','Settings');$('connection-button').after(gear);
  const theme=dbutton('REI · Advanced',()=>profileSettings(),'d-theme');theme.id='d-theme';theme.title='Settings';theme.setAttribute('aria-haspopup','dialog');$('source-list-label').after(theme);
  const evidence=$('evidence-area'),wrapper=dnode('div',{id:'d-evidence',role:'tabpanel'});while(evidence.firstChild)wrapper.append(evidence.firstChild);evidence.append(dnode('div',{id:'d-tabs',class:'d-tabs',role:'tablist','aria-label':'Workspace tabs'}),wrapper,dnode('div',{id:'d-content',class:'d-content',role:'tabpanel',hidden:''}));
  document.querySelector('.ai-controls').append(dnode('span',{id:'d-budget-alert',class:'d-muted',role:'status','aria-live':'polite'}));
  renderTabs();$('ai-guidance-preferences').hidden=true;
  if(HOSTED_DEMO)return;
  window.addEventListener('discovery-ai-settings-open',()=>renderAISettingsDetails().catch(error=>{$('ai-discovery-settings').replaceChildren(dnode('p',{class:'d-muted',text:error.message}));}));
  window.addEventListener('discovery-backend-ready',()=>requiresLocal().catch(()=>{}));
  if(state.health)await requiresLocal().catch(()=>{});
}
async function hydrateDiscovery(){
  try{const data=await dapi('/bootstrap');Object.assign(D,{ready:true,profiles:data.profiles,levels:data.levels,tools:data.tools,settings:data.settings,budget:data.budget});await useProfile(data.profiles.find(p=>p.id===data.settings.active_profile));updateBudgetBadge();document.querySelector('footer').append(dnode('span',{class:'d-muted',text:'Make human knowledge accessible to everyone, from the first lesson to the frontiers of scientific discovery.'}));
    for(const input of [$('query'),$('constraint-deadline'),$('constraint-data'),$('constraint-mentor')])input.addEventListener('change',queueWorkspace);
    $('d-sensitive').checked=!!D.sensitive;
    window.addEventListener('beforeunload',event=>{if(D.dirty||D.saveError){event.preventDefault();event.returnValue='';}});
    D.hydrated=true;launchDefaultSearch();
  }catch(error){D.ready=false;throw new Error('Discovery setup failed: '+error.message);}
}
initDiscovery();
