'use strict';

const builtinSources = [
  {id:'pubmed', name:'PubMed', description:'Publication metadata and available abstracts.'},
  {id:'ensembl', name:'Ensembl', description:'Human genes and genomic regions in GRCh38.'},
  {id:'gwas', name:'GWAS Catalog', description:'Reported genetic associations with traits.'}
];
let sourceBarRequest = 0;

// Shared by the profile editor and the direct Manage themes panel.
function buildThemePicker(profile, {open=false, onChange=()=>{}}={}) {
  const section=dnode('section',{class:'d-theme-picker'}),heading=dnode('h3'),chips=dnode('div',{class:'d-chips'});
  const query=dfield('Search research categories','','search'),tree=dnode('div',{class:'d-tree'});
  const breadcrumbs=dnode('div',{class:'d-bar d-theme-breadcrumbs'});
  const catalogue=dnode('details',{open:open?'':null},[dnode('summary',{text:'Browse theme catalogue'}),query.wrapper,breadcrumbs,tree]);
  let current='WORLD';
  function change(themes) {
    if(themes.length>30){toast('Choose up to 30 themes for one profile.');render();return;}
    profile.themes=themes;onChange();render();
  }
  function render() {
    heading.textContent='Themes · '+profile.themes.length+' selected';
    chips.replaceChildren(...profile.themes.map(id=>dbutton((D.taxonomy.find(n=>n.id===id)?.name||id)+' ×',()=>change(profile.themes.filter(x=>x!==id)))));
    if(!profile.themes.length)chips.append(dnode('p',{class:'d-muted',text:'No specific themes selected. Add themes to focus future AI guidance and quizzes.'}));
    breadcrumbs.replaceChildren(dbutton('All branches',()=>{current='WORLD';query.input.value='';render();},'quiet small'));
    const ancestors=[];let node=D.taxonomy.find(n=>n.id===current);
    while(node&&node.id!=='WORLD'){ancestors.unshift(node);node=D.taxonomy.find(n=>n.id===node.parent_id);}
    for(const ancestor of ancestors)breadcrumbs.append(dbutton(ancestor.name,()=>{current=ancestor.id;query.input.value='';render();},'quiet small'));
    tree.replaceChildren();const term=query.input.value.trim().toLowerCase();
    const nodes=D.taxonomy.filter(n=>term?n.name.toLowerCase().includes(term)&&n.node_type!=='root':n.parent_id===current).slice(0,100);
    for(const item of nodes){
      const row=dnode('div',{class:'d-bar'});
      if(!['root','branch'].includes(item.node_type)){
        const choice=dcheck(item.name,profile.themes.includes(item.id));
        choice.input.onchange=()=>change(choice.input.checked?[...new Set([...profile.themes,item.id])]:profile.themes.filter(x=>x!==item.id));row.append(choice.wrapper);
      }else row.append(dnode('strong',{text:item.name}));
      if(D.taxonomy.some(n=>n.parent_id===item.id))row.append(dbutton('Browse ›',()=>{current=item.id;query.input.value='';render();},'quiet small'));
      tree.append(row);
    }
    if(!nodes.length)tree.append(dnode('p',{text:'No matching categories. Try a broader subject.'}));
  }
  query.input.oninput=render;
  section.append(heading,chips,dnode('div',{class:'d-bar'},[
    dbutton('Add theme',()=>{catalogue.open=true;query.input.focus();}),
    dbutton('Clear themes',()=>change([]),'quiet small')]),catalogue);
  render();return section;
}

function showCustomizationNotice() {
  const box=$('source-update-notice');
  if(!box)return;
  const undo=D.customizationUndo,applicable=!!undo&&undo.id===D.profile?.id&&undo.revision===D.profile?.revision;
  box.hidden=!applicable;
  box.replaceChildren();
  if(applicable)box.append(dnode('span',{role:'status',text:undo.message}),dbutton(undo.profileUpdate?'Roll back profile':'Undo',undoCustomization,'quiet small'));
}
function applyCustomizedProfile(profile) {
  const index=D.profiles.findIndex(p=>p.id===profile.id);
  if(index>=0)D.profiles[index]=profile;
  if(D.profile.id!==profile.id)return;
  D.profile=profile;cancelAI();cancelGuidance();guidanceCache.clear();
  applyProfile();resetTabBodies();selectTab(D.tab);updateGuidance();showCustomizationNotice();
  if(state.search)setNotice('Workspace settings changed. Run a new search to apply the current source selection.');
}
async function saveCustomization(changes,message) {
  const current=clone(D.profile);
  await D.saveQueue;
  const saved=await dapi('/profiles/save',{profile:{...current,...changes},base_revision:current.revision,create:false});
  D.customizationUndo={id:saved.id,revision:saved.revision,message};
  applyCustomizedProfile(saved);return saved;
}
async function undoCustomization() {
  const undo=D.customizationUndo;
  if(!undo||undo.id!==D.profile.id||undo.revision!==D.profile.revision)throw new Error('The profile has changed. Reopen Settings to review its latest revision.');
  const result=await dapi('/profiles/action',{id:undo.id,revision:undo.revision,action:'undo'});
  D.customizationUndo=null;applyCustomizedProfile(result);toast('Workspace change undone.');
}
async function manageThemes() {
  await requiresLocal();if(!D.taxonomy)D.taxonomy=(await dapi('/taxonomy')).nodes;
  const draft=clone(D.profile),{body,dialog}=drawer('Manage themes','themes-dialog');D.dirty=false;
  body.append(dnode('p',{text:'Choose research themes for '+draft.name+'. Future AI guidance and quizzes use these selections. Saved research and quiz history stay available.'}),
    buildThemePicker(draft,{onChange:()=>{D.dirty=true;}}),
    dnode('div',{class:'d-bar'},[dbutton('Save themes',async()=>{
      if(D.profile.id!==draft.id||D.profile.revision!==draft.revision)throw new Error('This profile changed. Close and reopen Manage themes before saving.');
      if(JSON.stringify([...draft.themes].sort())===JSON.stringify([...D.profile.themes].sort())){D.dirty=false;dialog.close();return;}
      const names=draft.themes.map(id=>D.taxonomy.find(n=>n.id===id)?.name||id);
      const title=names.length?(names.slice(0,2).join(' · ')+(names.length>2?' + '+(names.length-2)+' more':'')).slice(0,180):'General Learning & Research';
      await saveCustomization({themes:draft.themes,theme_title:title,provenance:{...draft.provenance,theme_title:{origin:'user'}}},'Themes updated for '+draft.name+'.');
      D.dirty=false;dialog.close();toast('Themes saved. Undo is available in the source bar.');
    },'primary'),dbutton('Cancel',()=>{D.dirty=false;dialog.close();})]));
}

async function profileSources(profile) {
  const [apis,databases]=await Promise.all([
    dapi('/api-connections?profile_id='+encodeURIComponent(profile.id)),dapi('/connections?profile_id='+encodeURIComponent(profile.id))]);
  return [...builtinSources.map(source=>({...source,kind:'evidence'})),
    ...apis.connections.map(item=>({id:'api:'+item.id,name:item.name,kind:'api',description:'Connected HTTPS JSON API',connection:item})),
    ...databases.connections.map(item=>({id:'sqlite:'+item.id,name:item.name,kind:'sqlite',description:'Connected read-only SQLite database',connection:item}))];
}
async function setSourceVisible(source,visible) {
  const hidden=new Set(D.profile.hidden_source_ids||[]);
  visible?hidden.delete(source.id):hidden.add(source.id);
  await saveCustomization({hidden_source_ids:[...hidden]},source.name+(visible?' added to':' removed from')+' this workspace.');
}
function sourceRow(source,action) {
  return dnode('article',{class:'d-row d-source-option','data-source-id':source.id},[
    dnode('div',{},[dnode('h3',{text:source.name}),dnode('p',{class:'d-muted',text:source.description})]),action]);
}
async function manageSources() {
  await requiresLocal();const profileId=D.profile.id,{body,dialog}=drawer('Manage sources','sources-dialog');
  async function render() {
    const sources=await profileSources(D.profile);if(!dialog.open||D.profile.id!==profileId)return;
    const active=sources.filter(source=>sourceVisible(D.profile,source.id));
    body.replaceChildren(dnode('p',{text:'Remove sources from this profile’s workspace. Their saved connections and datasets are kept, and Add source can restore them. Use the source checkboxes to temporarily include or exclude evidence searches.'}));
    const actions=dnode('div',{class:'d-bar'},[dbutton('+ Add source',()=>{dialog.close();return addSource();},'primary')]);
    if(D.customizationUndo?.id===profileId&&D.customizationUndo.revision===D.profile.revision)actions.append(dbutton('Undo',async()=>{await undoCustomization();await render();}));
    body.append(actions);
    if(!active.length)body.append(dnode('p',{text:'No sources in this workspace. Add a source to continue.'}));
    for(const source of active){
      const buttons=dnode('div',{class:'d-bar'});
      if(source.kind!=='evidence')buttons.append(dbutton(source.kind==='api'?'Explore API':'Browse tables',()=>{dialog.close();return source.kind==='api'?apiExplorer(source.connection):databaseBrowser(source.connection);}));
      buttons.append(dbutton('Remove from workspace',async()=>{await setSourceVisible(source,false);await render();},'quiet small'));
      body.append(sourceRow(source,buttons));
    }
  }
  await render();
}
async function addSource() {
  await requiresLocal();const profileId=D.profile.id,{body,dialog}=drawer('Add source','add-source-dialog');
  async function render() {
    const profile=clone(D.profile),sources=await profileSources(profile);
    if(!dialog.open||D.profile.id!==profileId)return;
    body.replaceChildren(dnode('p',{text:'Choose evidence sources for the search bar, restore a saved connection, or connect an API or database for this profile.'}),dnode('h3',{text:'Evidence search catalogue'}));
    for(const source of sources.filter(item=>item.kind==='evidence')){
      const action=sourceVisible(profile,source.id)?dnode('span',{class:'d-muted',text:'In workspace'}):dbutton('Add to workspace',async()=>{await setSourceVisible(source,true);await render();});
      body.append(sourceRow(source,action));
    }
    const removed=sources.filter(item=>item.kind!=='evidence'&&!sourceVisible(profile,item.id));
    if(removed.length){body.append(dnode('h3',{text:'Restore saved connections'}));for(const source of removed)body.append(sourceRow(source,dbutton('Add to workspace',async()=>{await setSourceVisible(source,true);await render();})));}
    const catalog=dnode('div'),openForm=(item)=>{dialog.close();apiConnectionForm({...item,id:null},profileId);};
    body.append(dnode('h3',{text:'Connect another source'}),dnode('p',{class:'d-muted',text:'Connected APIs and databases open in their own explorers. Retrieved data goes through privacy review before AI analysis.'}),
      dnode('div',{class:'d-bar'},[
        dbutton('Connect to an API',()=>{dialog.close();apiConnectionForm(null,profileId);},'primary'),
        dbutton('Connect SQLite database',()=>{dialog.close();connectionForm();}),
        dbutton('Recommend APIs with AI',async()=>{
          if(!state.health?.ai.configured){openAISetup();return;}
          const value=await dapi('/api-connections/recommend',{profile_id:profileId},{timeout:270000});
          if(dialog.open&&D.profile.id===profileId)renderAPICatalog(catalog,value.recommendations,profileId,value.provenance,openForm);
        })]),catalog);
    const services=await dapi('/api-connections/catalog');
    if(dialog.open&&D.profile.id===profileId)renderAPICatalog(catalog,services.services,profileId,null,openForm);
  }
  await render();
}
async function refreshSourceBar() {
  const request=++sourceBarRequest,profile=D.profile,connected=$('connected-source-shortcuts');
  for(const source of builtinSources)$('source-'+source.id).closest('.source-chip').hidden=!sourceVisible(profile,source.id);
  const empty=$('empty-source-selection');empty.hidden=builtinSources.some(source=>sourceVisible(profile,source.id));
  showCustomizationNotice();connected.replaceChildren();connected.hidden=true;
  if(!D.ready)return;
  try{
    const sources=(await profileSources(profile)).filter(source=>source.kind!=='evidence'&&sourceVisible(profile,source.id));
    if(request!==sourceBarRequest||D.profile?.id!==profile.id)return;
    connected.hidden=!sources.length;
    if(sources.length)connected.append(dnode('span',{class:'d-muted',text:'Connected sources'}));
    for(const source of sources.slice(0,3)){
      const button=dbutton(source.name,()=>source.kind==='api'?apiExplorer(source.connection):databaseBrowser(source.connection),'quiet small');
      button.dataset.caption=source.kind==='api'?'Open this API to retrieve data, review privacy, and analyze an approved copy.':'Open this SQLite database to select tables and preview data with read-only access.';
      button.dataset.sourceId=source.id;connected.append(button);
    }
    if(sources.length>3){const more=dbutton('All connected sources ('+sources.length+')',manageSources,'quiet small');more.dataset.caption='Open the full list of connected APIs and databases to explore or manage them.';connected.append(more);}
  }catch(error){
    if(request!==sourceBarRequest)return;
    connected.hidden=false;connected.append(dnode('span',{class:'d-muted',text:'Connected sources could not be loaded. Open Manage sources to retry.'}));
  }
}
async function restoreRecommendedSources() {
  const hidden=D.profile?.hidden_source_ids||[];
  if(D.ready&&hidden.some(id=>builtinSources.some(source=>source.id===id)))await saveCustomization({hidden_source_ids:hidden.filter(id=>!builtinSources.some(source=>source.id===id))},'Recommended evidence sources restored.');
  cancelGuidance();for(const source of builtinSources)$('source-'+source.id).checked=true;
  state.prefs.sources=sourcePreferences();persistPrefs();if(D.ready)queueWorkspace();
  if(state.search)setNotice('Sources changed. Search again to retrieve evidence with these choices.');updateGuidance();toast('Recommended sources restored.');
}

function initCustomization() {
  const themeTools=dnode('div',{class:'d-profile-tools'}),theme=$('d-theme');
  theme.before(themeTools);themeTools.append(theme);
  const themes=dbutton('Manage themes',manageThemes,'quiet small');themes.id='manage-themes';themeTools.append(themes);
  const add=dbutton('+ Add source',addSource,'quiet small');add.id='add-source';
  const manage=dbutton('Manage sources',manageSources,'quiet small');manage.id='manage-sources';
  const actions=dnode('div',{class:'d-source-actions'},[add,manage]);
  const empty=dnode('span',{id:'empty-source-selection',class:'d-muted',text:'No evidence sources. Choose Add source.',hidden:''});
  document.querySelector('.source-choices').append(empty);
  $('source-strip').append(actions,dnode('div',{id:'connected-source-shortcuts',class:'d-connected-sources',hidden:''}),dnode('div',{id:'source-update-notice',class:'d-source-update',hidden:''}));
  const originalApply=applyProfile;
  applyProfile=function(){originalApply();refreshSourceBar();};
  window.addEventListener('discovery-sources-changed',refreshSourceBar);
  refreshSourceBar();
}
initCustomization();
