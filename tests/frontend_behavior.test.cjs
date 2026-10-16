// Pure JavaScript DOM test double. No browser automation, network, or API key.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { randomUUID } = require('node:crypto');

class Element {
  constructor(tag='div') { this.tagName=tag.toUpperCase();this.children=[];this.handlers={};this.attrs={};this.dataset={};this._text='';this.value='';this.hidden=false;this.disabled=false;this.open=false; }
  set textContent(value) { this._text=String(value);this.children=[]; }
  get textContent() { return this._text+this.children.map(c=>c.textContent).join(''); }
  append(...items) { for(const item of items){item.parentElement=this;this.children.push(item);if(this.tagName==='SELECT'&&!this.value)this.value=item.value;} }
  replaceChildren(...items) { this.children=[];this._text='';this.append(...items); }
  addEventListener(name,fn) { (this.handlers[name] ||= []).push(fn); }
  async dispatch(name,event={preventDefault(){}}) { for(const handler of this.handlers[name]||[])await handler(event); }
  setAttribute(key,value) { this.attrs[key]=value; }
  removeAttribute(key) { delete this.attrs[key]; }
  focus() {} showModal(){this.open=true;} close(){this.open=false;}
  click(){}
  cloneNode(deep){const e=new Element(this.tagName);e.className=this.className;e._text=this._text;e.src=this.src;e.href=this.href;e.attrs={...this.attrs};if(deep)e.append(...this.children.map(c=>c.cloneNode(true)));return e;}
  replaceWith(other){const parent=this.parentElement;if(!parent)return;const i=parent.children.indexOf(this);parent.children[i]=other;other.parentElement=parent;}
  get outerHTML(){const escape=s=>String(s||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');const attrs={...this.attrs,...(this.src?{src:this.src}:{}),...(this.href?{href:this.href}:{})};return `<${this.tagName.toLowerCase()}${Object.entries(attrs).map(([k,v])=>` ${k}="${escape(v)}"`).join('')}>${escape(this._text)}${this.children.map(c=>c.outerHTML).join('')}</${this.tagName.toLowerCase()}>`;}
  remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(c=>c!==this);}
  querySelectorAll(selector){const out=[];for(const child of this.children){if(selector.startsWith('.')?(child.className||'').split(' ').includes(selector.slice(1)):child.tagName===selector.toUpperCase())out.push(child);out.push(...child.querySelectorAll(selector));}return out;}
}

async function harness(turns=[], speechRecognition=null, speechSynthesis=null, timers={setTimeout,clearTimeout}, restoreFixture={}) {
  const source=fs.readFileSync('catnanny/web/static/chat.js','utf8');
  const html=fs.readFileSync('catnanny/web/static/simulator.html','utf8');
  const elements={};for(const match of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g))elements[match[2]]=new Element(match[1]);
  elements['messages'].append(elements.welcome);elements['report-days'].value='7';elements['voice-language'].value='en-US';
  const records=restoreFixture.storage||new Map(),calls=[],downloads=[],windowHandlers={};
  class TestURL extends URL{static createObjectURL(blob){downloads.push(blob);return 'blob:test';}static revokeObjectURL(){}}
  function exportDocument(){const documentElement=new Element('html'),head=new Element('head'),body=new Element('body');documentElement.append(head,body);return {documentElement,head,body,createElement:tag=>new Element(tag),querySelectorAll:s=>documentElement.querySelectorAll(s)};}
  const cats=[{cat_id:'mochi',name:'Mochi'},{cat_id:'jeremy',name:'Jeremy'}];
  const record={event_id:'evt_j',cat_id:'jeremy',cat_name:'Jeremy',event_type:'appetite',occurred_at:'2026-10-14T12:00:00Z',details:{status:'not_eating'},reporter:'Alex',status:'awaiting_answer',photos:[]};
  if(restoreFixture.record)Object.assign(record,restoreFixture.record);
  const report={cat:'Mochi',cat_id:'mochi',start:'2026-10-07T12:00:00Z',end:'2026-10-14T12:00:00Z',counts:{total_events:1},timeline:[{time:'2026-10-14T12:00:00Z',type:'vomit',reporter:'Alex',status:'completed',details:{content:'food'},photos:['http://localhost:8000/uploads/test.png']}]};
  const context={document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag),querySelectorAll:()=>[],addEventListener(){},implementation:{createHTMLDocument:exportDocument}},
    window:{addEventListener(name,fn){(windowHandlers[name] ||= []).push(fn);},SpeechRecognition:speechRecognition,speechSynthesis,SpeechSynthesisUtterance:speechSynthesis?class{constructor(text){this.text=text;}}:null},location:{origin:'http://localhost:8000'},localStorage:{getItem:key=>records.get(key)||null,setItem:(key,value)=>records.set(key,value),removeItem:key=>records.delete(key)},
    crypto:{randomUUID},URL:TestURL,URLSearchParams,Date,Blob,setTimeout:timers.setTimeout,clearTimeout:timers.clearTimeout,confirm:()=>true,alert(){},FileReader:class{readAsDataURL(blob){blob.arrayBuffer().then(buffer=>{this.result=`data:${blob.type};base64,${Buffer.from(buffer).toString('base64')}`;this.onload();});}},
    fetch:async(path,options={})=>{calls.push({path,body:options.body?JSON.parse(options.body):null});let data;
      if(path==='/cats')data=cats;
      else if(path==='/caregivers')data=[{caregiver_id:'demo_caregiver',name:'Alex'}];
      else if(path==='/capabilities')data={extraction_provider:'rules',ai_configured:false};
      else if(path==='/conversations/turns')data=turns.shift();
      else if(path.startsWith('/conversations/')){
        const url=new URL(path,'http://localhost'),parts=url.pathname.split('/');
        const saved=restoreFixture.sessions?.[decodeURIComponent(parts[2])];
        if(!saved)throw new Error('Unexpected conversation '+path);
        if(parts[3]==='messages'){
          const offset=Number(url.searchParams.get('offset')||0),size=restoreFixture.pageSize||200;
          data={items:saved.messages.slice(offset,offset+size),total:saved.messages.length};
        }else data=saved.state;
      }
      else if(path.startsWith('/reports/')){if(restoreFixture.failReports?.())throw new Error('Report unavailable');data=report;}
      else if(path.startsWith('/events/'))data=record;
      else if(path.startsWith('/uploads/'))return {ok:true,status:200,blob:async()=>new Blob(['test-image'],{type:'image/png'})};
      else throw new Error('Unexpected request '+path);
      return {ok:true,status:200,json:async()=>data};}};
  vm.runInNewContext(source,context);
  await new Promise(resolve=>setImmediate(resolve));
  return {elements,calls,records,report,downloads,record,async windowEvent(name,event={}){for(const fn of windowHandlers[name]||[])await fn(event);await new Promise(resolve=>setImmediate(resolve));}};
}

test('reports are requested explicitly and include a seven-day table with images',async()=>{
  const h=await harness();
  assert.equal(h.calls.some(c=>c.path.startsWith('/reports/')),false);
  await h.elements['report-open'].dispatch('click');
  assert.equal(h.calls.filter(c=>c.path.startsWith('/reports/')).length,1);
  const url=new URL(h.calls.at(-1).path,'http://localhost');
  assert.equal(url.searchParams.get('cat_id'),'mochi');
  assert.equal(new Date(url.searchParams.get('end'))-new Date(url.searchParams.get('start')),7*86400000);
  const table=h.elements['report-body'].querySelectorAll('table')[0];
  assert.ok(table);
  assert.deepEqual(table.querySelectorAll('th').map(e=>e.textContent),['Time','Observation / symptoms','Caregiver','Status','Photos']);
  assert.equal(table.querySelectorAll('img')[0].src,'/uploads/test.png');
  assert.match(table.textContent,/Food/);
});

test('initial message does not silently assign the default cat; name confirmation keeps both messages',async()=>{
  const h=await harness([
    {session_id:'pending',event_id:null,cat_id:null,status:'awaiting_cat',speech:'Which cat is this about?'},
    {session_id:'pending',event_id:'evt_j',cat_id:'jeremy',cat_name:'Jeremy',status:'awaiting_answer',speech:'When did Jeremy last eat?',upload_url:'/photos/upload?event_id=evt_j'}
  ]);
  h.elements['message-input'].value='My cat is not eating';await h.elements['chat-form'].dispatch('submit');
  const first=h.calls.find(c=>c.path==='/conversations/turns').body;
  assert.equal(first.cat_id,undefined);
  assert.equal(first.caregiver_id,'demo_caregiver');
  h.elements['message-input'].value='Jeremy';await h.elements['chat-form'].dispatch('submit');
  assert.match(h.elements['chat-title'].textContent,/Jeremy/);
  assert.match(h.elements.messages.textContent,/My cat is not eating/);
  assert.match(h.elements.messages.textContent,/Jeremy/);
  assert.equal(h.records.get('catnanny.session.jeremy'),'pending');
  assert.equal(h.records.get('catnanny.pendingSession'),undefined);
  assert.match(h.elements.messages.textContent,/SIMULATED TEXT MESSAGE/);
});

test('changing cat profiles gives report requests the selected cat only',async()=>{
  const h=await harness();
  const jeremy=h.elements['cat-list'].children[1];
  await jeremy.dispatch('click');
  await h.elements['report-open'].dispatch('click');
  const request=h.calls.find(c=>c.path.startsWith('/reports/'));
  assert.equal(new URL(request.path,'http://localhost').searchParams.get('cat_id'),'jeremy');
});

test('requested report downloads a standalone HTML table with embedded photos',async()=>{
  const h=await harness();
  await h.elements['report-open'].dispatch('click');
  assert.equal(h.downloads.length,0);
  await h.elements['report-html'].dispatch('click');
  assert.equal(h.downloads.length,1);
  const html=await h.downloads[0].text();
  assert.match(html,/<table/);
  assert.match(html,/Mochi/);
  assert.match(html,/data:image\/png;base64,/);
  assert.doesNotMatch(html,/localhost:8000\/uploads/);
});

test('subject correction updates the profile and photo card without leaving the session mapped to the old cat',async()=>{
  const h=await harness([
    {session_id:'same',event_id:'evt_j',cat_id:'mochi',cat_name:'Mochi',speech:'Saved for Mochi.',caregiver_id:'demo_caregiver',caregiver_name:'Alex'},
    {session_id:'same',event_id:'evt_j',cat_id:'jeremy',cat_name:'Jeremy',speech:'Corrected: this observation is about Jeremy.',caregiver_id:'demo_caregiver',caregiver_name:'Alex',ui_action:'observation_reassigned',action_payload:{from_cat_id:'mochi'}}
  ]);
  h.elements['message-input'].value='Mochi vomited';await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.records.get('catnanny.session.mochi'),'same');
  h.elements['message-input'].value='Actually I meant Jeremy';await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.records.get('catnanny.session.mochi'),undefined);
  assert.equal(h.records.get('catnanny.session.jeremy'),'same');
  assert.match(h.elements['chat-title'].textContent,/Jeremy/);
  assert.equal(h.elements.messages.querySelectorAll('.delivery-card')[0].querySelectorAll('strong')[0].textContent,'Add a photo for Jeremy');
  assert.match(h.elements.messages.textContent,/Corrected/);
});


test('interim-only voice transcription preserves drafts without auto-send',async()=>{
  let mic;
  class Recognition {
    constructor(){mic=this;}
    start(){}
    stop(){this.onend();}
    abort(){this.onend();}
  }
  const h=await harness([],Recognition);
  h.elements['message-input'].value='Mochi';
  await h.elements['voice-toggle'].dispatch('click');
  assert.equal(mic.lang,'en-US');
  assert.equal(h.elements['message-input'].disabled,true);
  mic.onresult({results:[[{transcript:'vomited'}]]});
  mic.onresult({results:[[{transcript:'vomited twice'}]]});
  assert.equal(h.elements['message-input'].value,'Mochi vomited twice');
  await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.calls.some(c=>c.path==='/conversations/turns'),false);
  mic.onend();
  assert.equal(h.elements['message-input'].disabled,false);
  assert.equal(h.elements['voice-toggle'].attrs['aria-pressed'],'false');
  assert.equal(h.calls.some(c=>c.path==='/conversations/turns'),false);
});

test('microphone failure keeps typed text and provides a retry explanation',async()=>{
  let mic;
  class Recognition {constructor(){mic=this;}start(){}stop(){this.onend();}}
  const h=await harness([],Recognition);
  h.elements['message-input'].value='Existing draft';
  await h.elements['voice-toggle'].dispatch('click');
  mic.onerror({error:'not-allowed'});mic.onend();
  assert.equal(h.elements['message-input'].value,'Existing draft');
  assert.match(h.elements['voice-hint'].textContent,/permission was denied/);
  assert.equal(h.elements['message-input'].disabled,false);
});

test('unsupported browsers retain typed input with an explicit voice fallback',async()=>{
  const h=await harness();
  assert.equal(h.elements['voice-toggle'].disabled,true);
  assert.match(h.elements['voice-hint'].textContent,/unavailable/);
  assert.equal(h.elements['message-input'].disabled,false);
});


test('new replies speak visible text; replay and mute cancel playback',async()=>{
  const spoken=[];let canceled=0;
  const synth={getVoices:()=>[],cancel(){canceled++;},speak(u){spoken.push(u);u.onstart();}};
  const h=await harness([{session_id:'audio',speech:'Which cat are you recording this for?'}],null,synth);
  assert.equal(spoken.length,0);
  h.elements['message-input'].value='My cat vomited';
  await h.elements['chat-form'].dispatch('submit');
  assert.equal(spoken.length,1);
  assert.equal(spoken[0].text,h.elements['device-subtitle'].textContent);
  assert.equal(spoken[0].lang,'en-US');
  assert.equal(h.elements['alexa-device'].attrs['data-state'],'speaking');
  spoken[0].onend();
  assert.equal(h.elements['alexa-device'].attrs['data-state'],'ready');
  await h.elements['audio-replay'].dispatch('click');
  assert.equal(spoken.length,2);
  const before=canceled;
  await h.elements['audio-toggle'].dispatch('click');
  assert.equal(canceled,before+1);
  assert.equal(h.records.get('catnanny.audio'),'off');
  spoken[1].onstart();
  assert.equal(h.elements['alexa-device'].attrs['data-state'],'ready');
});

test('microphone interrupts speech playback and disables replay while listening',async()=>{
  let mic,canceled=0;
  class Recognition{constructor(){mic=this;}start(){}stop(){this.onend();}}
  const synth={getVoices:()=>[],cancel(){canceled++;},speak(u){u.onstart();}};
  const h=await harness([{session_id:'audio',speech:'Which cat?'}],Recognition,synth);
  h.elements['message-input'].value='My cat vomited';await h.elements['chat-form'].dispatch('submit');
  const before=canceled;
  await h.elements['voice-toggle'].dispatch('click');
  assert.equal(canceled,before+1);
  assert.equal(h.elements['audio-replay'].disabled,true);
  assert.equal(h.elements['alexa-device'].attrs['data-state'],'listening');
  mic.onend();
  assert.equal(h.elements['audio-replay'].disabled,false);
});


test('final voice text sends after five seconds; editing or canceling stops the countdown',async()=>{
  let mic;const pending=new Map();let sequence=0;
  const timers={setTimeout(fn){const id=++sequence;pending.set(id,fn);return id;},clearTimeout(id){pending.delete(id);}};
  async function second(){for(const [id,fn]of [...pending]){pending.delete(id);fn();}await new Promise(resolve=>setImmediate(resolve));}
  class Recognition{constructor(){mic=this;}start(){}stop(){this.onend();}}
  const h=await harness([{session_id:'auto',speech:'Which cat?'}],Recognition,null,timers);
  h.elements['chat-form'].requestSubmit=()=>h.elements['chat-form'].dispatch('submit');
  async function dictate(){await h.elements['voice-toggle'].dispatch('click');const result=[{transcript:'My cat vomited'}];result.isFinal=true;mic.onresult({results:[result]});mic.onend();}
  await dictate();
  assert.match(h.elements['voice-hint'].textContent,/Sending in 5/);
  for(let i=0;i<4;i++)await second();
  assert.equal(h.calls.some(c=>c.path==='/conversations/turns'),false);
  await second();
  assert.equal(h.calls.filter(c=>c.path==='/conversations/turns').length,1);
  await dictate();
  await h.elements['voice-cancel'].dispatch('click');
  for(let i=0;i<5;i++)await second();
  assert.equal(h.calls.filter(c=>c.path==='/conversations/turns').length,1);
  await dictate();h.elements['message-input'].value='Corrected draft';
  await h.elements['message-input'].dispatch('input');
  for(let i=0;i<5;i++)await second();
  assert.equal(h.calls.filter(c=>c.path==='/conversations/turns').length,1);
  assert.equal(h.elements['message-input'].value,'Corrected draft');
});


test('page reload restores persisted session, paginated history, record and photos without replaying side effects',async()=>{
  const spoken=[];
  const synth={getVoices:()=>[],cancel(){},speak(u){spoken.push(u);}};
  const state={session_id:'resume',cat_id:'mochi',cat_name:'Mochi',event_id:'evt_j',
    status:'awaiting_answer',details:{status:'eating_less'},speech:'When did Mochi last eat normally?'};
  const first=await harness([state],null,synth);
  first.elements['message-input'].value='Mochi is eating less';
  await first.elements['chat-form'].dispatch('submit');
  assert.equal(first.records.get('catnanny.session.mochi'),'resume');
  assert.equal(spoken.length,1);
  spoken.length=0;
  const messages=[
    {text:'Mochi is eating less',response:state},
    {text:'Download report',response:{...state,speech:'Here is your report.',ui_action:'open_report',action_payload:{download_format:'html'}}},
    {text:'Show care log',response:{...state,speech:'Here is the care log.',ui_action:'open_care_log'}}
  ];
  const h=await harness([{...state,speech:'Saved.'}],null,synth,undefined,{
    storage:first.records,sessions:{resume:{state,messages}},pageSize:2,
    record:{cat_id:'mochi',cat_name:'Mochi',details:{status:'eating_less'},photos:[{url:'/uploads/resume.png'}]}
  });
  assert.match(h.elements['chat-title'].textContent,/Mochi/);
  assert.equal(h.elements.messages.querySelectorAll('.message').length,6);
  assert.match(h.elements.messages.textContent,/Mochi is eating less/);
  assert.match(h.elements.messages.textContent,/Here is your report/);
  assert.equal(h.elements['record'].hidden,false);
  assert.equal(h.elements['event-status'].textContent,'Needs detail');
  assert.match(h.elements['event-details'].textContent,/Eating less/);
  assert.equal(h.elements.photos.querySelectorAll('img')[0].src,'/uploads/resume.png');
  const pageCalls=h.calls.filter(c=>c.path.includes('/messages?'));
  assert.equal(pageCalls.length,2);
  assert.match(pageCalls[1].path,/offset=2/);
  assert.equal(spoken.length,0);
  assert.equal(h.downloads.length,0);
  assert.equal(h.elements['report-dialog'].open,false);
  assert.equal(h.elements['history-dialog'].open,false);
  assert.equal(h.calls.some(c=>c.path.startsWith('/reports/')),false);
  assert.equal(h.calls.some(c=>c.path==='/conversations/turns'),false);
  h.elements['message-input'].value='12 hours';
  await h.elements['chat-form'].dispatch('submit');
  const payload=h.calls.find(c=>c.path==='/conversations/turns').body;
  assert.equal(payload.session_id,'resume');
  assert.equal(payload.cat_id,'mochi');
  assert.equal(payload.caregiver_id,'demo_caregiver');
  assert.notEqual(payload.request_id,first.calls.find(c=>c.path==='/conversations/turns').body.request_id);
});

test('reload preserves unanswered subject clarification without silently choosing the displayed cat',async()=>{
  const state={session_id:'pending',cat_id:null,cat_name:null,event_id:null,status:'awaiting_cat',speech:'Which cat is this about?'};
  const first=await harness([state]);
  first.elements['message-input'].value='My cat vomited';await first.elements['chat-form'].dispatch('submit');
  assert.equal(first.records.get('catnanny.pendingSession'),'pending');
  const h=await harness([state],null,null,undefined,{storage:first.records,
    sessions:{pending:{state,messages:[{text:'My cat vomited',response:state}]}}});
  assert.match(h.elements.messages.textContent,/Which cat/);
  assert.equal(h.calls.some(c=>c.path.startsWith('/events/')),false);
  h.elements['message-input'].value='Mochi';await h.elements['chat-form'].dispatch('submit');
  const payload=h.calls.find(c=>c.path==='/conversations/turns').body;
  assert.equal(payload.session_id,'pending');
  assert.equal(Object.hasOwn(payload,'cat_id'),false);
});

test('reload keeps pending confirmation in the same session for a subsequent yes answer',async()=>{
  const state={session_id:'confirm',cat_id:'mochi',cat_name:'Mochi',event_id:'evt_j',
    status:'awaiting_confirmation',speech:'Should I create Jeremy and move this observation? Please say yes or no.'};
  const storage=new Map([['catnanny.selectedCat','mochi'],['catnanny.session.mochi','confirm']]);
  const h=await harness([state],null,null,undefined,{storage,
    sessions:{confirm:{state,messages:[{text:'Actually Jeremy',response:state}]}}});
  assert.match(h.elements.messages.textContent,/Please say yes or no/);
  h.elements['message-input'].value='Yes';await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.calls.find(c=>c.path==='/conversations/turns').body.session_id,'confirm');
});


test('an action with no event clears old record fields and attached photos',async()=>{
  const h=await harness([
    {session_id:'old',cat_id:'mochi',event_id:'evt_j',speech:'Observation saved.'},
    {session_id:'old',cat_id:'mochi',event_id:null,speech:'Which observation?',ui_action:'refresh_record'}
  ],null,null,undefined,{record:{photos:[{url:'/uploads/old.png'}]}});
  h.elements['message-input'].value='Mochi is not eating';await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.elements.record.hidden,false);
  assert.equal(h.elements.photos.querySelectorAll('img').length,1);
  h.elements['message-input'].value='Refresh record';await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.elements.record.hidden,true);
  assert.equal(h.elements['record-empty'].hidden,false);
  assert.equal(h.elements['event-details'].children.length,0);
  assert.equal(h.elements.photos.children.length,0);
  assert.equal(h.elements['event-type'].textContent,'');
});

test('failed report reload cannot download a previously successful report',async()=>{
  let fail=false,autoClicks=0;
  const h=await harness([{session_id:'report',cat_id:'mochi',event_id:null,speech:'Requested report.',
    ui_action:'open_report',action_payload:{download_format:'json'}}],null,null,undefined,{failReports:()=>fail});
  await h.elements['report-open'].dispatch('click');
  assert.equal(h.elements['report-download'].disabled,false);
  fail=true;
  h.elements['report-download'].click=()=>{autoClicks++;};
  h.elements['message-input'].value='Download report';await h.elements['chat-form'].dispatch('submit');
  assert.match(h.elements['report-body'].textContent,/Could not load/);
  assert.equal(h.elements['report-download'].disabled,true);
  assert.equal(h.elements['report-html'].disabled,true);
  assert.equal(autoClicks,0);
  await h.elements['report-download'].dispatch('click');
  await h.elements['report-html'].dispatch('click');
  assert.equal(h.downloads.length,0);
  fail=false;
  await h.elements['report-open'].dispatch('click');
  await h.elements['report-download'].dispatch('click');
  assert.equal(h.downloads.length,1);
});

test('Chinese backend speech is displayed and spoken verbatim without duplicating follow-up',async()=>{
  const spoken=[],speech='我还没有 Jeremy 的档案。是否创建并更正归属？请回答是或否。';
  const synth={getVoices:()=>[],cancel(){},speak(u){spoken.push(u);}};
  const h=await harness([{session_id:'cn',cat_id:'mochi',event_id:null,status:'awaiting_confirmation',
    speech,follow_up:speech,missing_fields:['confirmation']}],null,synth);
  h.elements['message-input'].value='其实是 Jeremy';await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.elements['device-subtitle'].textContent,speech);
  assert.equal(h.elements.messages.querySelectorAll('.bubble').filter(e=>e.textContent===speech).length,1);
  assert.equal(spoken.length,1);
  assert.equal(spoken[0].text,speech);
  assert.equal(spoken[0].lang,'zh-CN');
  assert.doesNotMatch(h.elements.messages.textContent,/This observation has been saved/);
});


test('uploaded photos add one conversation note and repeated refreshes do not repeat it',async()=>{
  const h=await harness([{session_id:'photo',cat_id:'mochi',event_id:'evt_j',speech:'Saved.'}]);
  h.elements['message-input'].value='Mochi is not eating';await h.elements['chat-form'].dispatch('submit');
  assert.equal(h.elements.messages.querySelectorAll('.photo-update-note').length,0);
  h.record.photos=[{photo_id:'new-photo',url:'/uploads/new.png'}];
  await h.windowEvent('message',{origin:'http://localhost:8000',data:{type:'catnanny:photo-uploaded',eventId:'evt_j'}});
  assert.equal(h.elements.photos.querySelectorAll('img').length,1);
  const notes=h.elements.messages.querySelectorAll('.photo-update-note');
  assert.equal(notes.length,1);assert.match(notes[0].textContent,/Photo uploaded/);
  assert.equal(notes[0].parentElement,h.elements.messages.querySelectorAll('.delivery-card')[0]);
  await h.windowEvent('focus');
  await h.elements['refresh-photos'].dispatch('click');
  assert.equal(h.elements.messages.querySelectorAll('.photo-update-note').length,1);
  h.record.photos.push({photo_id:'second-photo',url:'/uploads/second.png'});
  await h.windowEvent('focus');
  assert.equal(h.elements.messages.querySelectorAll('.photo-update-note').length,1);
  assert.match(h.elements.messages.querySelectorAll('.photo-update-note')[0].textContent,/2 photos attached/);
});

test('restored photos show a confirmation once and unrelated upload messages do not refresh',async()=>{
  const state={session_id:'photo',cat_id:'mochi',event_id:'evt_j',speech:'Saved.'};
  const h=await harness([],null,null,undefined,{
    storage:new Map([['catnanny.session.mochi','photo']]),
    sessions:{photo:{state,messages:[{text:'Mochi is not eating',response:state}]}},
    record:{photos:[{photo_id:'old',url:'/uploads/old.png'}]}
  });
  assert.equal(h.elements.messages.querySelectorAll('.photo-update-note').length,1);
  await h.windowEvent('focus');
  assert.equal(h.elements.messages.querySelectorAll('.photo-update-note').length,1);
  const before=h.calls.length;
  await h.windowEvent('message',{origin:'https://unrelated.example',data:{type:'catnanny:photo-uploaded',eventId:'evt_j'}});
  await h.windowEvent('message',{origin:'http://localhost:8000',data:{type:'catnanny:photo-uploaded',eventId:'other-event'}});
  assert.equal(h.calls.length,before);
});


test('cross-tab storage upload notification refreshes photos without requiring window.opener',async()=>{
  const h=await harness([{session_id:'photo',cat_id:'mochi',event_id:'evt_j',speech:'Saved.'}]);
  h.elements['message-input'].value='Mochi is not eating';await h.elements['chat-form'].dispatch('submit');
  h.record.photos=[{photo_id:'cross-tab',url:'/uploads/cross-tab.png'}];
  await h.windowEvent('storage',{key:'catnanny.photo-uploaded',newValue:JSON.stringify({eventId:'evt_j'})});
  assert.equal(h.elements.photos.querySelectorAll('img').length,1);
  assert.match(h.elements.messages.querySelectorAll('.photo-update-note')[0].textContent,/Photo uploaded/);
  await h.windowEvent('storage',{key:'catnanny.photo-uploaded',newValue:JSON.stringify({eventId:'evt_j'})});
  assert.equal(h.elements.messages.querySelectorAll('.photo-update-note').length,1);
});
