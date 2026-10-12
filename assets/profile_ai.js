'use strict';

// Profile changes are available on demand in Settings; only Generate preview invokes AI.
let profileSearchContext=null,profileSearchRequest=0;
const profileFieldLabels={goal:'Learning or research goal',theme_title:'Theme summary',themes:'Research themes',learning_level:'Learning level',tabs:'Visible tabs',default_tab:'Initial tab',panels:'Side panels',eyebrow:'Workspace heading',heading:'Description lead-in',introduction:'Workspace description',examples:'Search examples'};
const profileLayoutFields=new Set(['tabs','default_tab','panels']);
function profileFieldLabel(field){const key=field.replace(/^ui\./,'');return profileFieldLabels[key]||key.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());}
function profileDisplayValue(field,value){
  if(field==='themes')return value.map(id=>D.taxonomy?.find(n=>n.id===id)?.name||id).join('\n')||'No themes';
  if(field==='learning_level')return quizLevelName(value);
  return Array.isArray(value)?value.join('\n')||'None':value||'(empty)';
}

function renderProfileSearchTip(){
  const box=$('profile-search-tip');if(!box)return;
  const valid=D.ready&&D.profile&&profileSearchContext&&!D.sensitive&&!state.searchController&&!state.search?.demo&&profileSearchContext.profile_id===D.profile.id&&profileSearchContext.revision===D.profile.revision&&profileSearchContext.latest_related&&profileSearchContext.searches.length;
  box.hidden=!valid;
  if(valid)$('profile-search-reason').textContent=profileSearchContext.searches.length+' recent '+(profileSearchContext.searches.length===1?'search matches':'searches match')+' your profile topics. Review a proposed update when you are ready.';
}
async function refreshProfileSearchContext(){
  const request=++profileSearchRequest;
  profileSearchContext=null;renderProfileSearchTip();
  if(!D.ready||D.sensitive)return;
  const {id,revision}=D.profile;
  try{
    const result=await dapi('/profiles/'+id+'/recent-searches');
    if(request!==profileSearchRequest||D.profile.id!==id||D.profile.revision!==revision)return;
    profileSearchContext=result;renderProfileSearchTip();
  }catch{/* The manual Settings entry remains available if history cannot load. */}
}

async function rollbackProfile(profile){
  await D.saveQueue;
  const restored=await dapi('/profiles/action',{id:profile.id,revision:profile.revision,action:'undo'});
  D.customizationUndo=null;applyCustomizedProfile(restored);
  toast('Previous profile restored. Saved research is still available.');
  return restored;
}

function renderProfileUpdateSection(body,dialog,{instruction='',searches=[]}={}){
  const base=clone(D.profile),section=dnode('section',{class:'d-settings-section d-profile-update','aria-label':'Update profile with AI'});
  const request=dfield('What would you like to update?',instruction,'textarea');request.input.id='profile-update-request';request.input.maxLength=8000;
  request.input.placeholder='For example: focus my research on ovarian aging and update the search examples.';
  const level=dcheck('Allow a learning-level change requested in my instructions');level.input.id='profile-update-level';
  const layout=dcheck('Allow changes to visible tabs and side panels');layout.input.id='profile-update-layout';
  const sensitive=dcheck('This request contains sensitive information',!!D.sensitive);sensitive.input.id='profile-update-sensitive';
  const status=dnode('p',{class:'d-status',role:'status'}),preview=dnode('section',{id:'profile-update-preview',hidden:'','aria-label':'Proposed profile changes'});
  const cancel=dbutton('Cancel preparation',()=>{clearPreview();dstatus(status,'Preparation canceled. Your profile has not changed.');});
  cancel.id='profile-update-cancel';cancel.dataset.caption='Stop waiting for this preview and keep your profile unchanged. AI usage already incurred may still be recorded.';
  const waiting=dnode('div',{id:'profile-update-working',class:'d-bar',hidden:''},[cancel]);
  let proposal=null,controller=null,sequence=0;
  function stopWorking(){waiting.hidden=true;preview.setAttribute('aria-busy','false');generate.textContent='Generate preview';}
  function startWorking(){waiting.hidden=false;preview.setAttribute('aria-busy','true');generate.textContent='AI is working…';}
  function clearPreview(){sequence++;controller?.abort();controller=null;stopWorking();proposal=null;preview.hidden=true;preview.replaceChildren();dstatus(status,'');}
  for(const input of [request.input,level.input,layout.input,sensitive.input])input.addEventListener('input',clearPreview);
  dialog.addEventListener('close',()=>{clearPreview();section.remove();},{once:true});
  section.append(dnode('h3',{text:'Update profile with AI'}),dnode('p',{class:'d-muted',text:'Active profile: '+base.name+' · '+quizLevelName(base.learning_level)+'. Describe your goal, then review the proposed changes before applying them.'}));
  if(searches.length){
    section.append(dnode('p',{class:'d-muted',text:'These completed searches matched words in your profile topics. Only the queries below are included; edit or remove them in your request.'}),
      dnode('ul',{class:'d-profile-searches'},searches.map(s=>dnode('li',{text:s.query+' — matches: '+s.matched_terms.join(', ')}))));
  }
  function current(){
    if(D.profile.id!==base.id||D.profile.revision!==base.revision)throw new Error('This profile changed. Reopen Update profile to review the current version.');
  }
  const generate=dbutton('Generate preview',async()=>{
    let run=sequence;
    try{
      current();const instruction=request.input.value.trim();
      if(!instruction)throw new Error('Describe the profile update you want.');
      if(!state.health?.ai.configured){openAISetup();return;}
      clearPreview();run=sequence;
      const payload={task:'adapt_profile',profile:base,instruction,allow_level_change:level.input.checked,allow_layout_changes:layout.input.checked,sensitive:sensitive.input.checked||!!D.sensitive,consent_ai:false};
      if(payload.sensitive){payload.consent_ai=await reviewSensitiveRequest(payload);if(!payload.consent_ai||sequence!==run||!dialog.open)return;}
      controller=new AbortController();const active=controller;
      startWorking();
      const result=await dapi('/ai/draft',payload,{timeout:270000,signal:active.signal});
      if(active.signal.aborted||sequence!==run||!dialog.open)return;
      current();if(result.base_revision!==base.revision)throw new Error('The draft uses an older profile. Generate a new preview.');
      if(!D.taxonomy)D.taxonomy=(await dapi('/taxonomy')).nodes;
      if(active.signal.aborted||sequence!==run||!dialog.open)return;
      proposal=result;stopWorking();showPreview();dstatus(status,result.changes.length?'Preview ready. Select the changes you want to apply.':'No profile changes needed.');
    }catch(error){if(sequence===run&&dialog.open)dstatus(status,error.name==='AbortError'?'The AI request timed out. Please try again. Your profile has not changed.':error.message,true);}
    finally{if(sequence===run){controller=null;stopWorking();}}
  },'primary');generate.id='profile-update-generate';
  generate.dataset.caption='Ask the connected AI to propose changes to this profile. Review the preview before anything is saved.';
  const clear=dbutton('Clear request',()=>{clearPreview();request.input.value='';request.input.focus();});clear.dataset.caption='Clear these instructions and discard the unsaved profile preview.';
  section.append(request.wrapper,level.wrapper,layout.wrapper,sensitive.wrapper,
    dnode('p',{class:'d-muted',text:'Your profile changes only when you select Apply selected changes. Roll back profile restores the previous saved version.'}),
    dnode('div',{class:'d-bar'},[generate,clear]),waiting,status,preview);
  body.append(section);

  function showPreview(){
    preview.hidden=false;preview.replaceChildren(dnode('h3',{text:proposal.changes.length?'Review proposed changes':'No profile changes needed'}));
    const explanation=dnode('p',{text:proposal.explanation});decorate(explanation,proposal.provenance);
    preview.append(explanation,dnode('small',{class:'d-origin',text:proposal.cached?'Checked against your saved profile · no AI request made.':originLabel(proposal)}));
    const changes=proposal.changes,choices=[];
    if(!changes.length){preview.append(dnode('p',{text:proposal.decision==='repeated_request'?'This repeats an update already reflected in your profile. No new profile version was saved.':'Your profile already fits this request. No new profile version was saved.'}));preview.scrollIntoView({block:'start'});return;}
    const layoutChanges=changes.filter(c=>profileLayoutFields.has(c.field));
    const groups=changes.filter(c=>!profileLayoutFields.has(c.field)).map(c=>({label:profileFieldLabel(c.field),changes:[c],checked:c.field!=='learning_level'}));
    if(layoutChanges.length)groups.push({label:'Workspace layout (tabs and side panels)',changes:layoutChanges,checked:false});
    for(const group of groups){
      const choice=dcheck('Apply '+group.label,group.checked);choices.push({input:choice.input,changes:group.changes});
      const row=dnode('div',{class:'d-row d-profile-change'},[choice.wrapper]);
      for(const change of group.changes){
        const before=dnode('p',{text:profileDisplayValue(change.field,change.before)}),after=dnode('p',{text:profileDisplayValue(change.field,change.after)});
        decorate(before,base.provenance[change.field.replace(/^ui\./,'')]);decorate(after,proposal.provenance);
        row.append(dnode('div',{class:'d-profile-diff'},[
          dnode('div',{},[dnode('strong',{text:'Current · '+profileFieldLabel(change.field)}),before]),
          dnode('div',{},[dnode('strong',{text:'Proposed'}),after]) ]));
      }
      preview.append(row);
    }
    const apply=dbutton('Apply selected changes',async()=>{
      try{
        current();if(!proposal)throw new Error('Generate a new preview after editing your request.');
        const selected=choices.filter(c=>c.input.checked).flatMap(c=>c.changes);
        if(!selected.length)throw new Error('Select at least one proposed change.');
        const updated=clone(base);
        for(const change of selected){
          const key=change.field.replace(/^ui\./,'');
          if(change.field.startsWith('ui.'))updated.ui[key]=clone(change.after);else updated[key]=clone(change.after);
          updated.provenance[key]=clone(proposal.profile.provenance[key]);
        }
        await D.saveQueue;current();
        const saved=await dapi('/profiles/save',{profile:updated,base_revision:base.revision,create:false});
        D.customizationUndo={id:saved.id,revision:saved.revision,message:'AI profile update applied to '+saved.name+'.',profileUpdate:true};
        applyCustomizedProfile(saved);
        dialog.close();toast('Profile updated. Roll back profile is available in Settings and the Sources tab.');
      }catch(error){dstatus(status,error.message,true);status.scrollIntoView({block:'nearest'});}
    },'primary');apply.id='profile-update-apply';apply.dataset.caption='Save only the selected changes and update this workspace. The previous profile remains available for rollback.';
    const discard=dbutton('Discard preview',clearPreview);discard.dataset.caption='Discard this AI proposal and keep the currently saved profile.';
    preview.append(dnode('div',{class:'d-bar'},[apply,discard]));
    preview.scrollIntoView({block:'start'});
  }
  return request.input;
}

async function updateProfileFromSearches(){
  await refreshProfileSearchContext();
  if(!profileSearchContext?.latest_related||!profileSearchContext.searches.length){toast('No recent related searches are available. Describe your update in Settings.');return;}
  const searches=clone(profileSearchContext.searches);
  const instruction='Suggest a focused update to my research or learning goal and workspace wording based on these recent searches. Preserve my other interests and current learning level.\n\nRecent search queries:\n'+searches.map(s=>'- '+s.query).join('\n');
  const {body,dialog}=drawer('Update profile from recent searches','profile-update-dialog');
  const input=renderProfileUpdateSection(body,dialog,{instruction,searches});
  input.focus();input.setSelectionRange(0,0);input.scrollTop=0;
}

function initProfileUpdates(){
  const originalApply=applyProfile;
  applyProfile=function(){originalApply();decorate($('d-theme').querySelectorAll('small')[1],D.profile.provenance.goal);};
  const originalUse=useProfile;
  useProfile=async function(profile){state.searchController?.abort();return originalUse(profile);};
}
initProfileUpdates();
