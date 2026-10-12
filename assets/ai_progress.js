'use strict';

// Every AI request goes through fetchBounded, including connection checks.
// One shared indicator follows the visible dialog and tracks concurrent work.
window.AIWork=(()=>{
  const pending=new Map();let counter=0,panel=null,title=null,message=null,list=null,timer=null,observer=null,headerObserver=null,observedHeader=null;
  const node=(tag,attributes={},text='')=>{const item=document.createElement(tag);for(const [key,value] of Object.entries(attributes))item.setAttribute(key,value);if(text)item.textContent=text;return item;};
  function taskName(url,options){
    const path=new URL(url,location.href).pathname;
    if(!/^\/api\/(?:ai(?:\/(?:check|configure))?|discovery\/(?:ai\/[^/]+|api-connections\/recommend|datasets\/[^/]+\/ask|library\/[^/]+\/analyze))$/.test(path))return '';
    if(path.endsWith('/ai/check'))return 'Checking AI connection';
    if(path.endsWith('/ai/configure'))return 'Saving AI connection settings';
    if(path.endsWith('/api-connections/recommend'))return 'Finding API recommendations';
    if(/\/library\/[^/]+\/analyze$/.test(path))return 'Analyzing saved material';
    if(/\/datasets\/[^/]+\/ask$/.test(path))return 'Analyzing your reviewed dataset';
    let payload={};try{payload=JSON.parse(options.body||'{}');}catch{/* A malformed request still gets a working indicator. */}
    return {create_quiz:'Creating an 8-question quiz',create_profile:'Drafting profile wording',update_profile:'Updating profile wording',adapt_profile:'Preparing profile preview',
      explain:'Explaining source evidence',questions:'Developing research questions',compare:'Comparing research briefs',guidance:'Preparing research guidance',answer:'Preparing an AI answer'}[payload.task||payload.action]||'Preparing an AI response';
  }
  function create(){
    panel=node('section',{id:'ai-work-status',class:'d-ai-work-status','aria-labelledby':'ai-work-heading'});
    title=node('strong',{id:'ai-work-heading'});message=node('p',{class:'d-ai-work-message',role:'status','aria-live':'polite'});
    list=node('div',{class:'d-ai-work-list','aria-busy':'true'});panel.append(title,message,list);
    observer=new MutationObserver(place);observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['open']});
    headerObserver=new ResizeObserver(place);
    window.addEventListener('resize',place);document.addEventListener('focusin',place);
  }
  function place(){
    if(!pending.size||!panel)return;
    const dialogs=[...document.querySelectorAll('dialog[open]')];
    const dialog=document.activeElement?.closest('dialog[open]')||dialogs.at(-1);
    const host=dialog||document.body,header=dialog?.querySelector(':scope > header');
    if(header!==observedHeader){headerObserver.disconnect();observedHeader=header;if(header)headerObserver.observe(header);}
    panel.classList.toggle('d-ai-work-floating',!dialog);
    panel.style.setProperty('--ai-work-top',(header?.getBoundingClientRect().height||0)+'px');
    if(panel.parentNode!==host||header&&header.nextElementSibling!==panel){if(header)header.after(panel);else host.append(panel);}
  }
  function update(){
    if(!panel)return;
    title.textContent=pending.size>1?'AI is working · '+pending.size+' tasks':'AI is working';
    let longest=0;
    for(const work of pending.values()){
      const seconds=Math.floor((Date.now()-work.started)/1000);longest=Math.max(longest,seconds);
      const text='Elapsed '+Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');
      if(work.elapsed.textContent!==text)work.elapsed.textContent=text;
    }
    const text=longest>=45?'AI is still working. Thank you for your patience.':'Please wait. Detailed requests can take a few minutes.';
    if(message.textContent!==text)message.textContent=text;
  }
  function begin(url,options={},signal){
    const label=taskName(url,options);if(!label||signal?.aborted)return ()=>{};
    if(!panel)create();
    const id=++counter,row=node('div',{class:'d-ai-work-item','data-ai-task':label});
    const heading=node('div',{class:'d-ai-work-label'}),elapsed=node('small',{'aria-live':'off'});
    heading.append(node('span',{},label),elapsed);
    const bar=node('div',{class:'d-ai-progress',role:'progressbar','aria-label':label});bar.append(node('span',{'aria-hidden':'true'}));
    row.append(heading,bar);list.append(row);pending.set(id,{started:Date.now(),elapsed});
    update();place();if(timer===null)timer=setInterval(update,1000);
    const finish=()=>{
      signal?.removeEventListener('abort',finish);if(!pending.delete(id))return;row.remove();
      if(pending.size){update();place();return;}
      clearInterval(timer);timer=null;observer.disconnect();headerObserver.disconnect();observedHeader=null;
      window.removeEventListener('resize',place);document.removeEventListener('focusin',place);
      panel.remove();panel=null;
    };
    signal?.addEventListener('abort',finish,{once:true});return finish;
  }
  return {begin};
})();
