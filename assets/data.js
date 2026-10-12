/* API sources and local privacy review share the same approved dataset workflow. */
async function renderDataConnections(box){
  window.dispatchEvent(new Event('discovery-sources-changed'));
  const profile=clone(D.profile),list=dnode('div'),catalog=dnode('div');
  const toolbar=dnode('div',{class:'d-bar'},[dbutton('Connect to an API',()=>apiConnectionForm(null,profile.id),'primary'),
    dbutton('Recommend APIs with AI',async()=>{
      if(!state.health?.ai.configured){openAISetup();return;}
      const result=await dapi('/api-connections/recommend',{profile_id:profile.id},{timeout:270000});
      const saved=await dapi('/api-connections?profile_id='+profile.id);
      if(D.profile.id===profile.id&&box.isConnected)renderAPICatalog(catalog,result.recommendations,profile.id,result.provenance,null,saved.connections);
    }),dbutton('Connect SQLite database',()=>connectionForm()),dbutton('Refresh',()=>renderDataConnections(box))]);
  if(profile.hidden_source_ids.some(id=>id.startsWith('api:catalog-')))toolbar.append(dbutton('Restore API suggestions',async()=>{
    await saveCustomization({hidden_source_ids:D.profile.hidden_source_ids.filter(id=>!id.startsWith('api:catalog-'))},'API suggestions restored.');
  }));
  box.replaceChildren(dnode('h3',{text:'Connections'}),toolbar,list,dnode('h3',{text:'Available APIs'}),catalog);
  const [apis,databases,services]=await Promise.all([dapi('/api-connections?profile_id='+profile.id),dapi('/connections?profile_id='+profile.id),dapi('/api-connections/catalog')]);
  if(!box.isConnected||D.profile.id!==profile.id)return;
  const visibleAPIs=apis.connections.filter(item=>sourceVisible(profile,'api:'+item.id));
  const visibleDatabases=databases.connections.filter(item=>sourceVisible(profile,'sqlite:'+item.id));
  renderAPICatalog(catalog,services.services.filter(service=>!apis.connections.some(item=>item.url===service.url)),profile.id);
  if(!visibleAPIs.length&&!visibleDatabases.length)list.append(dnode('p',{class:'d-muted',text:apis.connections.length+databases.connections.length?'Saved connections are removed from this workspace. Restore them with Add source.':'No connections for this profile yet.'}));
  for(const item of visibleAPIs)list.append(apiConnectionRow(services.services.find(service=>service.url===item.url),item,profile.id));
  for(const item of visibleDatabases){
    const remove=dbutton('Delete',async()=>{
      if(!confirm('Delete this database connection? Saved datasets and the original database will remain.'))return;
      await dapi('/connections/'+item.id+'/disconnect',{});refreshConnectionViews(profile.id);
    },'quiet small d-danger');
    remove.dataset.caption='Delete this saved database connection after confirmation. The original database and saved datasets remain.';
    list.append(dnode('article',{class:'d-row d-item-row'},[
      dnode('div',{class:'d-item-info'},[dnode('h3',{text:item.name}),dnode('p',{class:'d-item-summary',text:'SQLite · '+item.storage+' · read-only'})]),
      dnode('div',{class:'d-item-actions'},[dbutton('Browse tables',()=>databaseBrowser(item)),remove])]));
  }
}
function refreshConnectionViews(profileId){
  if(D.profile.id!==profileId)return;
  resetTabBodies();selectTab(D.tab);window.dispatchEvent(new Event('discovery-sources-changed'));
}
function apiConnectionRow(service,connection,profileId,provenance=null,onEdit=null){
  const item=connection||service,status=dnode('p',{class:'d-status d-connection-status',role:'status'});
  const info=dnode('div',{class:'d-item-info'},[dnode('h3',{text:item.name})]);
  if(service)info.append(dnode('p',{class:'d-item-summary',text:service.reason||service.description}));
  info.append(dnode('p',{class:'d-item-summary d-wrap-text',text:item.url}),status);
  if(service?.documentation)info.append(dnode('a',{class:'d-api-docs',href:service.documentation,target:'_blank',rel:'noopener noreferrer',text:'API documentation ↗'}));
  if(provenance)info.append(dnode('small',{class:'d-origin',text:originLabel({provenance})}));
  const actions=dnode('div',{class:'d-item-actions'});
  const row=dnode('article',{class:'d-row d-item-row d-api-row '+(provenance?'d-ai':'d-source')},[info,actions]);
  if(service)row.dataset.serviceId=service.id;
  let busy=false;
  async function run(action){
    if(busy)return;
    if(D.profile.id!==profileId)throw new Error('Reopen Connections for the active profile.');
    busy=true;actions.querySelectorAll('button').forEach(button=>button.disabled=true);
    try{await action();}catch(error){dstatus(status,error.message,true);}
    finally{busy=false;actions.querySelectorAll('button').forEach(button=>button.disabled=false);}
  }
  function showConnection(){
    row.classList.toggle('d-api-connection',!!connection);
    if(connection)row.dataset.connectionId=connection.id;else delete row.dataset.connectionId;
    connectButton.textContent=connection?'Reconnect':'Connect';
    connectButton.dataset.caption=connection?'Test this API using its saved settings and credentials.':'Test and save this public API connection for the active profile.';
    dstatus(status,connection?'Connected · checked '+new Date(connection.checked_at).toLocaleString():'Not connected');
  }
  async function connect(){
    dstatus(status,connection?'Reconnecting…':'Connecting…');
    if(connection){
      const result=await dapi('/api-connections/'+connection.id+'/check',{profile_id:profileId},{timeout:30000});
      connection.checked_at=new Date().toISOString();showConnection();dstatus(status,result.message);
      if(D.profile.id===profileId&&!sourceVisible(D.profile,'api:'+connection.id))await saveCustomization({hidden_source_ids:D.profile.hidden_source_ids.filter(id=>id!=='api:'+connection.id)},'API connection restored.');
    }else{
      // A second catalogue row may already have connected this preset.
      const saved=await dapi('/api-connections?profile_id='+profileId);
      connection=saved.connections.find(value=>value.url===service.url&&value.auth_type==='none');
      if(connection){await connect();return;}
      const {name,url,query_parameter,rows_path,parameters}=service;
      connection=await dapi('/api-connections',{profile_id:profileId,name,url,query_parameter,rows_path,parameters,auth_type:'none'},{timeout:30000});
      showConnection();refreshConnectionViews(profileId);
    }
  }
  const editButton=dbutton('Edit connection',()=>run(()=>{
    const value=connection||{...service,id:null};
    return onEdit?onEdit(value):apiConnectionForm(value,profileId);
  }));
  const connectButton=dbutton('Connect',()=>run(connect));
  const explore=dbutton('Explore API',()=>run(async()=>{
    if(!connection)await connect();
    if(D.profile.id===profileId)await apiExplorer(connection);
  }));
  explore.dataset.caption='Open the API explorer to retrieve and review data. An available public API is connected first.';
  const remove=dbutton('Delete',()=>run(async()=>{
    const message=connection?'Delete this API connection and its saved credentials? Reviewed datasets will remain.':'Remove this API suggestion from this profile? Restore API suggestions in Connections to bring it back.';
    if(!confirm(message))return;
    if(connection)await dapi('/api-connections/'+connection.id+'/disconnect',{profile_id:profileId});
    if(service&&D.profile.id===profileId){
      const hidden=[...new Set([...D.profile.hidden_source_ids,'api:catalog-'+service.id])];
      await saveCustomization({hidden_source_ids:hidden},'API removed. Restore API suggestions in Connections to add it again.');
    }else refreshConnectionViews(profileId);
    row.remove();
  }),'quiet small d-danger');
  remove.dataset.caption='Delete the saved API connection and credentials after confirmation, or remove an unconnected suggestion. Reviewed datasets remain.';
  actions.append(editButton,connectButton,explore,remove);showConnection();return row;
}
function renderAPICatalog(box,services,profileId,provenance=null,onEdit=null,connections=[]){
  box.classList.add('d-api-catalog');
  box.replaceChildren();
  const visible=services.filter(item=>sourceVisible(D.profile,'api:catalog-'+item.id));
  if(provenance)box.append(dnode('p',{class:'d-muted',text:'AI recommendations for this profile. Connect to verify access.'}));
  if(!visible.length)box.append(dnode('p',{class:'d-muted',text:'No additional API suggestions.'}));
  for(const item of visible)box.append(apiConnectionRow(item,connections.find(value=>value.url===item.url),profileId,provenance,onEdit));
}

function apiConnectionForm(existing=null,profileId=D.profile.id){
  const returnTab=D.tab==='sources'?'sources':'connections';
  const {body,dialog}=drawer(existing?.id?'Edit API connection':'Connect to an API','api-connect-dialog');
  const name=dfield('Connection name',existing?.name||''),url=dfield('API URL',existing?.url||'','url');
  const auth=dselect('Authentication',[['none','Public — no credentials'],['bearer','Bearer token'],['api_key_header','API key in header'],['api_key_query','API key in query'],['basic','Username and password']],existing?.auth_type||'none');
  const username=dfield('Username','','text'),credential=dfield('Password or API token','','password'),authName=dfield('API key header or parameter name',existing?.auth_name||'X-API-Key');
  credential.input.autocomplete='new-password';username.input.autocomplete='off';
  credential.input.placeholder=existing?.id?'Leave blank to keep credentials for the same endpoint':'Enter the credential required by the service';
  const query=dfield('Search parameter (optional)',existing?.query_parameter||''),rowsPath=dfield('Records path (optional)',existing?.rows_path||'');
  query.input.placeholder='e.g. q or query.term';rowsPath.input.placeholder='e.g. data or message.items';
  const parameters=dfield('Fixed query parameters (JSON)',JSON.stringify(existing?.parameters||{},null,2),'textarea');
  const options=dnode('details',{},[dnode('summary',{text:'API query options'}),query.wrapper,rowsPath.wrapper,parameters.wrapper,
    dnode('p',{class:'d-muted',text:'Use the service documentation to select its records array and page size. This connector supports HTTPS JSON GET endpoints; OAuth sign-in and write operations are not supported.'})]);
  function authFields(){const kind=auth.input.value;username.wrapper.hidden=kind!=='basic';credential.wrapper.hidden=kind==='none';authName.wrapper.hidden=!kind.startsWith('api_key');}
  auth.input.onchange=authFields;authFields();
  const status=dnode('p',{class:'d-status',role:'status'});
  body.append(dnode('p',{text:'Saved for this profile. Testing retrieves a bounded response without sending it to AI. Credentials are encrypted locally and excluded from library exports.'}),name.wrapper,url.wrapper,auth.wrapper,username.wrapper,credential.wrapper,authName.wrapper,options,status,
    dbutton('Test & save connection',async()=>{
      if(!name.input.value.trim()||!url.input.reportValidity())throw new Error('Provide a name and API URL.');
      let fixed;try{fixed=JSON.parse(parameters.input.value||'{}');}catch{throw new Error('Use a JSON object for fixed query parameters.');}
      dstatus(status,'Testing the API…');
      try{
        const item=await dapi('/api-connections',{id:existing?.id||null,profile_id:profileId,name:name.input.value,url:url.input.value.trim(),
          auth_type:auth.input.value,auth_name:authName.input.value,username:username.input.value,credential:credential.input.value,
          query_parameter:query.input.value.trim(),rows_path:rowsPath.input.value.trim(),parameters:fixed},{timeout:30000});
        dialog.close();resetTabBodies();selectTab(returnTab);window.dispatchEvent(new Event('discovery-sources-changed'));await apiExplorer(item);
      }catch(error){dstatus(status,error.message,true);}finally{credential.input.value='';username.input.value='';}
    },'primary'));
  dialog.addEventListener('close',()=>{credential.input.value='';username.input.value='';},{once:true});
}

async function apiExplorer(connection){
  const {body}=drawer(connection.name,'api-explorer-dialog');
  const search=dfield('Search this API','','search'),status=dnode('p',{class:'d-status',role:'status'}),working=dnode('div');
  search.input.placeholder=connection.query_parameter?'Enter a topic or terms for this API':'This endpoint has no search parameter';
  search.input.disabled=!connection.query_parameter;
  body.append(dnode('p',{class:'d-wrap-text',text:connection.url}),dnode('p',{text:'Retrieve records, review their privacy, then ask questions or calculate statistics from the working copy.'}),search.wrapper,
    dbutton('Retrieve data',async()=>{
      dstatus(status,'Retrieving one response…');
      try{const stage=await dapi('/api-connections/'+connection.id+'/query',{profile_id:connection.profile_id,query:search.input.value},{timeout:30000});
        dstatus(status,stage.scope+' '+stage.total+' records received.');
        await privacyReview(stage,async item=>{working.replaceChildren(dnode('h3',{text:'Reviewed API working copy'}));await datasetAnalysisPanel(working,item.id);resetTabBodies();selectTab(D.tab);});
      }catch(error){dstatus(status,error.message,true);}
    },'primary'),status,working);
  const waiting=dfield('Question about connected data','','textarea');waiting.input.disabled=true;waiting.input.placeholder='Review a retrieved snapshot to enable questions about these data.';working.append(waiting.wrapper);
}

async function importDataset(){
  await requiresLocal();const profileId=D.profile.id;
  const {body,dialog}=drawer('Import dataset','dataset-import-dialog'),file=dnode('input',{type:'file',accept:'.csv,.json'}),status=dnode('p',{class:'d-status',role:'status'});
  body.append(dnode('p',{text:'Import CSV or a JSON array (up to 8 MB, 5,000 rows, and 100 columns). Your original file remains unchanged. Privacy detection and preview run locally.'}),
    dnode('label',{},['Dataset file',file]),status,dbutton('Review privacy',async()=>{
      if(!file.files[0])throw new Error('Choose a CSV or JSON dataset.');
      dstatus(status,'Reading and checking fields locally…');
      try{const stage=await dapi('/datasets/import',{profile_id:profileId,filename:file.files[0].name,file_base64:await dbase64(file.files[0])},{timeout:30000});dialog.close();await privacyReview(stage);}
      catch(error){dstatus(status,error.message,true);}
    },'primary'));
}

async function privacyReview(stage,onSaved=async item=>{resetTabBodies();selectTab('datasets');await openActivity(item.id);}){
  const {body,dialog}=drawer('Review dataset privacy','dataset-review-dialog');
  let previewId=null,offset=0,saved=false,revision=0;const rules=[];
  dialog.addEventListener('close',()=>{if(!saved)dapi('/dataset-reviews/'+stage.stage_id+'/discard',{}).catch(()=>{});},{once:true});
  body.append(dnode('p',{text:stage.total+' rows · local review only. Select what to keep, replace, mask, or remove. AI will receive only the working copy you approve.'}),
    dnode('p',{class:'notice',text:'Automatic detection is a starting point. Review identifying columns, free text, and rare combinations. Pseudonymized data is not guaranteed anonymous.'}));
  const originals=dnode('details',{},dnode('summary',{text:'Original preview — stays local (first 5 rows)'})),originalTable=dnode('div');renderTable(originalTable,stage.original_preview);originals.append(originalTable);body.append(originals);
  if(stage.original_available===false)body.append(dnode('p',{class:'d-muted',text:'No retained original is available for this copy. Review its current values, or reimport the original to restore removed fields.'}));
  const grid=dnode('div',{class:'d-privacy-fields'});
  const copyName=dfield('Working copy name','Reviewed dataset');body.append(copyName.wrapper);
  const actions=[['keep','Keep'],['pseudonymize','Replace with labels'],['remove','Remove'],['mask','Mask'],['year','Year only'],['band','Numeric bands of 10']];
  for(const rule of stage.rules){
    const info=stage.fields.find(field=>field.field===rule.field),action=dselect('Protection for '+rule.field,actions,rule.action),label=dfield('Replacement label for '+rule.field,rule.label);
    action.input.disabled=info.required_remove;
    const row=dnode('section',{class:'d-privacy-rule'},[dnode('strong',{class:'d-wrap-text',text:rule.field}),dnode('small',{text:info.reason}),action.wrapper,label.wrapper]);
    label.wrapper.hidden=rule.action!=='pseudonymize';
    action.input.onchange=()=>{label.wrapper.hidden=action.input.value!=='pseudonymize';invalidate();};label.input.oninput=invalidate;
    rules.push({field:rule.field,action:action.input,label:label.input});grid.append(row);
  }
  const terms=dfield('Additional sensitive values (one per line)',(stage.terms||[]).join('\n'),'textarea');terms.input.rows=3;terms.input.oninput=invalidate;
  const retained=dcheck('Keep an encrypted private original on this computer so I can revise rules later',false);
  const approved=dcheck('I reviewed the transformed data and approve saving this working copy',false);
  const status=dnode('p',{class:'d-status',role:'status'}),preview=dnode('div',{class:'d-privacy-preview d-source'}),caption=dnode('p',{class:'d-muted'});
  function invalidate(){revision++;previewId=null;approved.input.checked=false;save.disabled=true;dstatus(status,'Rules changed. Preview the updated copy before saving.');}
  async function updatePreview(){
    const current=++revision;previewId=null;approved.input.checked=false;save.disabled=true;
    const value=await dapi('/dataset-reviews/'+stage.stage_id+'/preview',{rules:rules.map(r=>({field:r.field,action:r.action.value,label:r.label.value})),terms:terms.input.value.split('\n').map(x=>x.trim()).filter(Boolean),offset});
    if(current!==revision)return;
    previewId=value.preview_id;renderTable(preview,value.rows);caption.textContent=`Working copy · ${value.total} rows · page ${Math.floor(offset/50)+1}`;
    approved.input.checked=false;save.disabled=true;dstatus(status,'Preview ready. Review the copy, then confirm below.');
  }
  const save=dbutton('Save reviewed working copy',async()=>{
    if(!previewId||!approved.input.checked)throw new Error('Preview and approve the current working copy first.');
    const item=await dapi('/dataset-reviews/'+stage.stage_id+'/save',{preview_id:previewId,reviewed:true,retain_original:retained.input.checked,title:copyName.input.value.trim()});saved=true;dialog.close();await onSaved(item);
  },'primary');save.disabled=true;approved.input.onchange=()=>save.disabled=!previewId||!approved.input.checked;
  body.append(grid,terms.wrapper,dbutton('Preview working copy',()=>{offset=0;return updatePreview();},'primary'),status,caption,preview,
    dnode('div',{class:'d-bar'},[dbutton('Previous preview page',()=>{offset=Math.max(0,offset-50);return updatePreview();}),dbutton('Next preview page',()=>{if(offset+50<stage.total)offset+=50;return updatePreview();})]),
    retained.wrapper,dnode('p',{class:'d-muted',text:'Private originals and replacement mappings are encrypted and excluded from library ZIPs and AI requests. Without a retained original, reimport it to undo removals. Working copies remain marked sensitive in ZIP export review.'}),approved.wrapper,save);
}

async function datasetAnalysisPanel(body,id,initialQuestion=''){
  const privacy=await dapi('/datasets/'+id+'/privacy'),panel=dnode('section',{class:'d-analysis'}),status=dnode('p',{class:'d-status',role:'status'});
  body.append(panel);panel.append(dnode('h3',{text:'Learning and research with this dataset'}),dnode('p',{class:'d-privacy-status',text:privacy.reviewed?'Reviewed working copy · pseudonymized · not guaranteed anonymous':'Privacy review required — AI analysis is disabled'}),
    dbutton(privacy.reviewed?'Revise privacy rules':'Review privacy and create working copy',async()=>privacyReview(await dapi('/datasets/'+id+'/review',{}))));
  if(!privacy.reviewed)return;
  panel.append(dnode('p',{class:'d-muted',text:'Source: '+privacy.source+' · reviewed '+new Date(privacy.reviewed_at).toLocaleString()}));
  const question=dfield('Question about connected data',initialQuestion,'textarea');question.input.placeholder='Ask about patterns, comparisons, study limitations, or what to learn next.';
  const consent=dcheck('Send my question and this reviewed working copy to the connected AI',false),output=dnode('div',{class:'d-analysis-output',tabindex:'-1'}),statistics=dnode('div');
  panel.append(dnode('p',{class:'d-muted',text:'Statistics use all rows in this saved copy. AI receives those statistics and a bounded sample of up to 100 rows. Original data and replacement mappings are never sent to AI.'}),
    dbutton('Calculate statistics',async()=>{const value=await dapi('/datasets/'+id+'/statistics');statistics.replaceChildren(dnode('p',{text:value.row_count+' rows. '+value.scope}));renderStatistics(statistics,value.columns);}),statistics,
    question.wrapper,consent.wrapper,dbutton('Ask AI about this copy',async()=>{
      if(!state.health?.ai.configured){openAISetup();return;}
      if(!question.input.value.trim()||!consent.input.checked)throw new Error('Enter a question and authorize use of the reviewed copy.');
      dstatus(status,'Analyzing the reviewed copy…');
      try{const result=await dapi('/datasets/'+id+'/ask',{question:question.input.value.trim(),consent_ai:true},{timeout:270000});
        output.replaceChildren(dnode('p',{class:'d-muted',text:'Question sent: '+result.question}),dnode('article',{class:'d-ai d-analysis-answer'},[
          dnode('small',{class:'d-origin',text:originLabel(result)}),dnode('p',{text:result.answer}),...result.limitations.map(text=>dnode('p',{text})),
          dnode('small',{text:`AI sample: ${result.sample_size} of ${result.row_count} saved rows; statistics cover the saved copy.`})]));dstatus(status,'Analysis ready.');output.focus({preventScroll:true});output.scrollIntoView({block:'start'});
      }catch(error){dstatus(status,error.message,true);}
    },'primary'),status,output);
}

function renderStatistics(box,columns){
  const table=dnode('div');box.append(table);renderTable(table,columns.map(value=>({Field:value.field,Type:value.kind,Present:value.present,Missing:value.missing,
    Summary:value.kind==='numeric'?`Mean ${value.mean}; median ${value.median}; min ${value.minimum}; max ${value.maximum}`:`${value.distinct} distinct; ${value.most_common.map(([v,n])=>v+' ('+n+')').join(', ')}`})));
}

const originalMaterialEditor=materialEditor;
materialEditor=async function(kind,...args){return kind==='dataset'?importDataset():originalMaterialEditor(kind,...args);};
const originalOpenActivity=openActivity;
openActivity=async function(id,archive=null){
  await originalOpenActivity(id,archive);
  if(!archive){const item=await dapi('/library/'+id);if(item.kind==='dataset')await datasetAnalysisPanel($('activity-dialog').querySelector('.d-body'),id);}
};
renderConnections=renderDataConnections;
