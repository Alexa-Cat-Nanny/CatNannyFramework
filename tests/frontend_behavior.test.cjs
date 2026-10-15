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

async function harness(turns=[]) {
  const source=fs.readFileSync('catnanny/web/static/chat.js','utf8');
  const html=fs.readFileSync('catnanny/web/static/simulator.html','utf8');
  const elements={};for(const match of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g))elements[match[2]]=new Element(match[1]);
  elements['messages'].append(elements.welcome);elements['report-days'].value='7';
  const records=new Map(),calls=[],downloads=[];
  class TestURL extends URL{static createObjectURL(blob){downloads.push(blob);return 'blob:test';}static revokeObjectURL(){}}
  function exportDocument(){const documentElement=new Element('html'),head=new Element('head'),body=new Element('body');documentElement.append(head,body);return {documentElement,head,body,createElement:tag=>new Element(tag),querySelectorAll:s=>documentElement.querySelectorAll(s)};}
  const cats=[{cat_id:'mochi',name:'Mochi'},{cat_id:'jeremy',name:'Jeremy'}];
  const record={event_id:'evt_j',cat_id:'jeremy',cat_name:'Jeremy',event_type:'appetite',occurred_at:'2026-10-14T12:00:00Z',details:{status:'not_eating'},reporter:'Alex',status:'awaiting_answer',photos:[]};
  const report={cat:'Mochi',cat_id:'mochi',start:'2026-10-07T12:00:00Z',end:'2026-10-14T12:00:00Z',counts:{total_events:1},timeline:[{time:'2026-10-14T12:00:00Z',type:'vomit',reporter:'Alex',status:'completed',details:{content:'food'},photos:['http://localhost:8000/uploads/test.png']}]};
  const context={document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag),querySelectorAll:()=>[],addEventListener(){},implementation:{createHTMLDocument:exportDocument}},
    window:{addEventListener(){}},location:{origin:'http://localhost:8000'},localStorage:{getItem:key=>records.get(key)||null,setItem:(key,value)=>records.set(key,value),removeItem:key=>records.delete(key)},
    crypto:{randomUUID},URL:TestURL,URLSearchParams,Date,Blob,setTimeout,confirm:()=>true,alert(){},FileReader:class{readAsDataURL(blob){blob.arrayBuffer().then(buffer=>{this.result=`data:${blob.type};base64,${Buffer.from(buffer).toString('base64')}`;this.onload();});}},
    fetch:async(path,options={})=>{calls.push({path,body:options.body?JSON.parse(options.body):null});let data;
      if(path==='/cats')data=cats;
      else if(path==='/caregivers')data=[{caregiver_id:'demo_caregiver',name:'Alex'}];
      else if(path==='/capabilities')data={extraction_provider:'rules',ai_configured:false};
      else if(path==='/conversations/turns')data=turns.shift();
      else if(path.startsWith('/reports/'))data=report;
      else if(path.startsWith('/events/'))data=record;
      else if(path.startsWith('/uploads/'))return {ok:true,status:200,blob:async()=>new Blob(['test-image'],{type:'image/png'})};
      else throw new Error('Unexpected request '+path);
      return {ok:true,status:200,json:async()=>data};}};
  vm.runInNewContext(source,context);
  await new Promise(resolve=>setImmediate(resolve));
  return {elements,calls,records,report,downloads};
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
