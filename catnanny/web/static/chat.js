/* Same-origin local household simulator. No API keys in the browser. */
(() => {
  const $ = id => document.getElementById(id);
  let profiles=[], people=[], selectedCat=null, sessionId=null, eventId=null, subjectConfirmed=false;
  let busy=false, retryPayload=null, latestReport=null, profileKind='cat', reportRun=0, historyOffset=0;
  const linkedEvents=new Set();
  const labels={content:'Vomit contents',has_blood:'Blood observed',episode_count:'Episodes',low_energy:'Lower energy',minutes_after_meal:'Minutes after food',status:'Appetite',hours_since_food:'Hours since normal meal'};
  const values={food:'Food',hairball:'Hairball',liquid:'Liquid',foam:'Foam',other:'Other',not_eating:'Not eating',eating_less:'Eating less',normal:'Normal'};
  const types={vomit:'Vomiting',appetite:'Appetite',litter:'Litter box',energy:'Energy',medication:'Medication',meal:'Meal'};
  function node(tag,cls,text){const e=document.createElement(tag); if(cls)e.className=cls; if(text!=null)e.textContent=text; return e;}
  function read(key){try{return localStorage.getItem(key);}catch{return null;}}
  function write(key,value){try{value?localStorage.setItem(key,value):localStorage.removeItem(key);}catch{}}
  function sessionKey(cat){return `catnanny.session.${cat}`;}
  function error(text){$('chat-error').textContent=text; $('chat-error').hidden=!text;}
  const synth=window.speechSynthesis, Utterance=window.SpeechSynthesisUtterance;
  const audioSupported=Boolean(synth&&Utterance);
  let audioEnabled=read('catnanny.audio')!=='off', activeSpeech=null, lastReply='';
  function restDevice(){if(!listening)deviceState(busy?'thinking':'ready',busy?'Thinking…':'Ready when you are');}
  function stopReply(){activeSpeech=null;if(audioSupported)synth.cancel();restDevice();}
  function renderAudio(){
    $('audio-toggle').disabled=!audioSupported;
    $('audio-toggle').setAttribute('aria-pressed',String(audioEnabled&&audioSupported));
    $('audio-toggle').textContent=audioSupported?`Voice replies: ${audioEnabled?'on':'off'}`:'Voice replies unavailable';
    $('audio-replay').disabled=!audioSupported||!lastReply||busy||listening;
  }
  function speakReply(text){
    if(!audioSupported||!text||listening)return;
    stopReply();
    try {
      const utterance=new Utterance(text);activeSpeech=utterance;
      utterance.lang=/[\u3400-\u9fff]/.test(text)?'zh-CN':'en-US';
      const voices=synth.getVoices();utterance.voice=voices.find(v=>v.lang===utterance.lang)||voices.find(v=>v.lang.startsWith(utterance.lang.slice(0,2)))||null;
      utterance.rate=1;
      utterance.onstart=()=>{if(activeSpeech!==utterance)return;deviceState('speaking','Speaking…');$('audio-status').textContent='Alexa is speaking…';};
      utterance.onend=()=>{if(activeSpeech!==utterance)return;activeSpeech=null;restDevice();$('audio-status').textContent='Reply finished. You can speak or type your next answer.';};
      utterance.onerror=()=>{if(activeSpeech!==utterance)return;activeSpeech=null;restDevice();$('audio-status').textContent='Audio could not play. Click Replay reply to try again.';};
      $('audio-status').textContent='Preparing voice reply…';synth.speak(utterance);
    }catch{activeSpeech=null;restDevice();$('audio-status').textContent='Audio could not play. Click Replay reply to try again.';}
  }
  $('audio-toggle').addEventListener('click',()=>{audioEnabled=!audioEnabled;write('catnanny.audio',audioEnabled?'on':'off');if(!audioEnabled)stopReply();renderAudio();$('audio-status').textContent=audioEnabled?'New replies will be read aloud.':'Voice replies muted.';});
  $('audio-replay').addEventListener('click',()=>{if(!busy&&!listening)speakReply(lastReply);});
  window.addEventListener('pagehide',stopReply);
  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  let recognition=null, listening=false, voiceBase='', voiceFailed=false, voiceHasFinal=false;
  let autoSendTimer=null, autoSendGeneration=0;
  function cancelAutoSend(){autoSendGeneration++;if(autoSendTimer!==null)clearTimeout(autoSendTimer);autoSendTimer=null;$('voice-cancel').hidden=true;}
  function scheduleAutoSend(){
    cancelAutoSend();const generation=autoSendGeneration,draft=$('message-input').value;let remaining=5;
    $('voice-cancel').hidden=false;
    function tick(){
      if(generation!==autoSendGeneration)return;
      if(busy||listening||document.hidden||$('message-input').value!==draft){cancelAutoSend();return;}
      if(remaining===0){cancelAutoSend();$('chat-form').requestSubmit();return;}
      $('voice-hint').textContent=`Sending in ${remaining} seconds… Edit the text or cancel to keep it as a draft.`;remaining--;autoSendTimer=setTimeout(tick,1000);
    }
    tick();
  }
  $('voice-cancel').addEventListener('click',()=>{cancelAutoSend();$('voice-hint').textContent='Auto-send canceled. Your text is kept for editing or manual sending.';});
  $('message-input').addEventListener('input',()=>{cancelAutoSend();$('voice-hint').textContent='Draft edited. Press Send when ready.';});
  $('caregiver-select').addEventListener('change',cancelAutoSend);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)cancelAutoSend();});
  window.addEventListener('pagehide',cancelAutoSend);
  function deviceState(state,label){$('alexa-device').setAttribute('data-state',state);$('device-status').textContent=label;}
  function finishVoice(){listening=false;$('voice-toggle').setAttribute('aria-pressed','false');$('voice-toggle').textContent='● Start speaking';$('voice-language').disabled=false;$('message-input').disabled=busy;renderAudio();if(!busy)deviceState(voiceFailed?'error':'ready',voiceFailed?'Microphone unavailable':'Ready when you are');}
  if(!Recognition){$('voice-toggle').disabled=true;$('voice-hint').textContent='Speech recognition is unavailable in this browser. Try Chrome, or type your observation.';}
  else {
    $('voice-toggle').addEventListener('click',()=>{
      if(busy)return;
      if(listening){recognition.stop();return;}
      cancelAutoSend();stopReply();voiceHasFinal=false;voiceBase=$('message-input').value.trim();voiceFailed=false;
      try {
        recognition=new Recognition();recognition.lang=$('voice-language').value;recognition.interimResults=true;recognition.continuous=false;
        recognition.onresult=e=>{let transcript='';for(let i=0;i<e.results.length;i++){transcript+=e.results[i][0].transcript+' ';if(e.results[i].isFinal&&e.results[i][0].transcript.trim())voiceHasFinal=true;}$('message-input').value=[voiceBase,transcript.trim()].filter(Boolean).join(' ').slice(0,4000);$('device-subtitle').textContent=transcript.trim()||'Listening…';};
        recognition.onerror=e=>{cancelAutoSend();voiceFailed=true;const hints={'not-allowed':'Microphone permission was denied. Allow access in browser settings, then retry.','audio-capture':'No microphone is available. Check your input device.','no-speech':'No speech detected. Click Start speaking to try again.',network:'Speech service could not connect. Check your network or type instead.'};$('voice-hint').textContent=hints[e.error]||'Speech recognition stopped. You can retry or type your observation.';};
        recognition.onend=()=>{finishVoice();if(!voiceFailed&&voiceHasFinal&&!busy)scheduleAutoSend();else if(!voiceFailed)$('voice-hint').textContent='No completed speech detected. Try again or type your answer.';};
        listening=true;$('message-input').disabled=true;$('voice-language').disabled=true;$('voice-toggle').textContent='■ Stop listening';$('voice-toggle').setAttribute('aria-pressed','true');deviceState('listening','Listening…');renderAudio();$('voice-hint').textContent='Speak now. Audio is handled by your browser’s speech service.';recognition.start();
      }catch{voiceFailed=true;finishVoice();$('voice-hint').textContent='Could not start speech recognition. Try again or type instead.';}
    });
    window.addEventListener('pagehide',()=>{if(listening)recognition.abort();});
  }
  function setBusy(value){busy=value; if(value){cancelAutoSend();voiceFailed=true;stopReply();}renderAudio(); if(value&&listening){recognition.abort();finishVoice();} $('voice-toggle').disabled=value||!Recognition; if(!activeSpeech)deviceState(value?'thinking':'ready',value?'Thinking…':'Ready when you are'); for(const id of ['send-message','new-conversation','message-input','caregiver-select','add-cat','add-caregiver'])$(id).disabled=value; $('send-message').textContent=value?'Thinking…':'Send ↑'; $('composer-status').textContent=value?'Understanding your observation…':'Enter to send · Shift + Enter for a new line';}
  async function api(path,options={}){let r;try{r=await fetch(path,options);}catch{throw new Error('Connection interrupted. Your input is kept for retry.');} const data=await r.json();if(!r.ok){const d=data.detail;const e=new Error(typeof d==='string'?d:d?.message||'Please check your input and try again.');e.status=r.status;throw e;}return data;}
  const post=(path,body)=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  function scroll(){$('messages').scrollTop=$('messages').scrollHeight;}
  function message(role,text,name){$('device-subtitle').textContent=text; $('welcome').hidden=true; const row=node('div',`message ${role}`),content=node('div','message-content');if(role==='assistant')row.append(node('div','message-avatar','✦'));content.append(node('div','message-label',role==='user'?(name||'You'):'CAT NANNY · Alexa simulation'),node('div','bubble',text));row.append(content);$('messages').append(row);scroll();return content;}
  function uploadLink(response,container){if(!response.event_id||linkedEvents.has(response.event_id))return;linkedEvents.add(response.event_id);const card=node('div','delivery-card');card.dataset.eventId=response.event_id;card.append(node('span','eyebrow','SIMULATED TEXT MESSAGE'),node('strong',null,`Add a photo for ${response.cat_name||'this cat'}`),node('p',null,'Photos attach to this observation. This card simulates delivery; no SMS or email is sent.'));const a=node('a',null,'Open photo upload ↗');a.href=`/photos/upload?event_id=${encodeURIComponent(response.event_id)}`;a.target='_blank';card.append(a);container.append(card);scroll();}
  function assistant(r,live=false){const text=r.speech||'';const content=message('assistant',text);uploadLink(r,content);lastReply=text;renderAudio();if(live&&audioEnabled)speakReply(text);}
  async function syncAction(r,previousCat,previousSession){
    if(r.ui_action==='observation_reassigned'&&previousCat&&previousCat!==r.cat_id&&read(sessionKey(previousCat))===previousSession)write(sessionKey(previousCat),null);
    if(['profiles_updated','caregiver_selected','observation_reassigned'].includes(r.ui_action)){
      try{const [newProfiles,newPeople]=await Promise.all([api('/cats'),api('/caregivers')]);profiles=newProfiles;people=newPeople;}catch{error('Action saved. Profile list refresh is temporarily unavailable.');}
      if(r.cat_id&&!profiles.some(c=>c.cat_id===r.cat_id))profiles.push({cat_id:r.cat_id,name:r.cat_name});
      if(r.caregiver_id&&!people.some(p=>p.caregiver_id===r.caregiver_id))people.push({caregiver_id:r.caregiver_id,name:r.caregiver_name});
      renderPeople(r.caregiver_id||$('caregiver-select').value);write('catnanny.caregiver',$('caregiver-select').value);
    }
    if(r.ui_action==='observation_reassigned')for(const card of $('messages').querySelectorAll('.delivery-card'))if(card.dataset.eventId===r.event_id){const heading=card.querySelectorAll('strong')[0];if(heading)heading.textContent=`Add a photo for ${r.cat_name}`;}
    if(r.ui_action==='open_photo_link')linkedEvents.delete(r.event_id);
  }
  async function requestedView(r){
    if(r.ui_action==='open_report'){const days=String(r.action_payload?.report_days||7);if(![...$('report-days').children].some(o=>o.value===days)){const option=node('option',null,`Last ${days} days`);option.value=days;$('report-days').append(option);}$('report-days').value=days;const report=await showReport();if(report&&report===latestReport&&r.action_payload?.download_format==='json')$('report-download').click();if(report&&report===latestReport&&r.action_payload?.download_format==='html')$('report-html').click();}
    if(r.ui_action==='open_care_log')await showHistory();
  }
  function format(value){return value==null?'Unknown':typeof value==='boolean'?(value?'Yes':'No'):values[value]||String(value);}
  const time=value=>new Date(value).toLocaleString('en-US');
  function imageURL(source){const url=new URL(source,location.origin);if(!['http:','https:'].includes(url.protocol))return null;return url.pathname.startsWith('/uploads/')?url.pathname:url.href;}
  function photoGrid(container,photos){container.replaceChildren();for(const p of photos){const src=imageURL(typeof p==='string'?p:p.url);if(!src)continue;const a=node('a');a.href=src;a.target='_blank';a.rel='noopener';const img=node('img');img.src=src;img.alt='Photo attached to this care observation';img.loading='lazy';a.append(img);container.append(a);}}
  function renderProfiles(){const host=$('cat-list');host.replaceChildren();for(const cat of profiles){const button=node('button',`companion-option${cat.cat_id===selectedCat?' selected':''}`);button.type='button';button.append(node('span','cat-avatar',cat.name[0].toUpperCase()),node('span',null,cat.name));button.setAttribute('aria-pressed',String(cat.cat_id===selectedCat));button.addEventListener('click',()=>selectCat(cat.cat_id,true));host.append(button);}const cat=profiles.find(c=>c.cat_id===selectedCat);$('chat-title').textContent=cat?`How is ${cat.name} today?`:'How is your companion today?';$('record-heading').textContent=cat?`${cat.name}’s current observation`:'Current observation';$('subject-note').textContent=subjectConfirmed&&cat?`Recording for ${cat.name}. Name a different companion to switch; each cat has a separate history.`:'Name a cat in your message. I will ask before saving if the subject is unclear.';write('catnanny.selectedCat',selectedCat);}
  function clearRecord(){
    $('record').hidden=true;$('record-empty').hidden=false;
    for(const id of ['event-type','event-status','event-time','event-caregiver'])$(id).textContent='';
    $('event-details').replaceChildren();$('photos').replaceChildren();
    $('photo-note').textContent='Photos stay with this observation.';
  }
  function clearStream(){cancelAutoSend();stopReply();lastReply='';renderAudio();for(const selector of ['.message','.photo-update-note'])for(const item of $('messages').querySelectorAll(selector))item.remove();linkedEvents.clear();$('welcome').hidden=false;clearRecord();eventId=null;retryPayload=null;error('');}
  function photoUpdateNote(data){
    for(const card of $('messages').querySelectorAll('.delivery-card')){
      if(card.dataset.eventId!==data.event_id)continue;
      let note=card.querySelectorAll('.photo-update-note')[0];
      if(!data.photos.length){if(note)note.remove();continue;}
      if(!note){note=node('div','photo-update-note');note.setAttribute('role','status');card.append(note);}
      const count=data.photos.length;
      note.replaceChildren(node('span','photo-update-icon','✓'),node('span',null,
        `Photo uploaded · ${count} ${count===1?'photo':'photos'} attached to this observation.`));
    }
  }
  async function refreshRecord(){const expected=eventId,cat=selectedCat;if(!expected){clearRecord();return;}const data=await api(`/events/${encodeURIComponent(expected)}?cat_id=${encodeURIComponent(cat)}`);if(eventId!==expected||selectedCat!==cat)return;$('record').hidden=false;$('record-empty').hidden=true;$('event-type').textContent=types[data.event_type]||data.event_type;$('event-status').textContent=data.status==='completed'?'Complete':data.status==='legacy'?'Logged':'Needs detail';$('event-time').textContent=time(data.occurred_at);$('event-caregiver').textContent=`First reported by ${data.reporter||'Not recorded'}`;$('event-details').replaceChildren();for(const [key,value]of Object.entries(data.details)){if(!labels[key])continue;const row=node('div','detail-row');row.append(node('dt',null,labels[key]),node('dd',null,format(value)));$('event-details').append(row);}photoGrid($('photos'),data.photos);photoUpdateNote(data);$('photo-note').textContent=data.photos.length?`${data.photos.length} photo(s) attached to this observation.`:'No photos yet. Use the upload link in the conversation.';}
  async function restore(id,expectedCat=null){sessionId=id;if(!id)return;const state=await api(`/conversations/${encodeURIComponent(id)}`);if(expectedCat&&state.cat_id&&state.cat_id!==expectedCat){write(sessionKey(expectedCat),null);sessionId=null;return;}if(state.cat_id&&state.cat_id!==selectedCat){selectedCat=state.cat_id;renderProfiles();}subjectConfirmed=Boolean(state.cat_id);renderProfiles();let offset=0;while(true){const page=await api(`/conversations/${encodeURIComponent(id)}/messages?limit=200&offset=${offset}`);for(const turn of page.items){message('user',turn.text||'Updated observation fields',turn.response.caregiver_name);assistant({...turn.response,...(turn.response.event_id===state.event_id?{cat_id:state.cat_id,cat_name:state.cat_name}:{})});}offset+=page.items.length;if(offset>=page.total||!page.items.length)break;}eventId=state.event_id;await refreshRecord();}
  async function selectCat(id,explicit=false){if(busy)return;setBusy(true);selectedCat=id;subjectConfirmed=explicit;sessionId=null;clearStream();renderProfiles();try{await restore(read(sessionKey(id)) || (explicit?read('catnanny.pendingSession'):null),id); if(explicit&&!eventId){subjectConfirmed=true;renderProfiles();}}catch(e){error('Unable to restore this cat’s conversation. You can start a new observation.');sessionId=null;}finally{setBusy(false);$('message-input').focus();}}
  $('chat-form').addEventListener('submit',async(e)=>{e.preventDefault();const text=$('message-input').value.trim();if(busy||listening||!text)return;cancelAutoSend();error('');const caregiverId=$('caregiver-select').value;const payload=retryPayload&&retryPayload.text===text&&retryPayload.session_id===sessionId&&retryPayload.caregiver_id===caregiverId?retryPayload:{request_id:crypto.randomUUID(),session_id:sessionId,text,source:'simulator',caregiver_id:caregiverId,...(subjectConfirmed?{cat_id:selectedCat}:{})};const replay=payload===retryPayload;if(!replay)message('user',text,people.find(p=>p.caregiver_id===caregiverId)?.name);retryPayload=payload;setBusy(true);try{const response=await post('/conversations/turns',payload);const previousCat=selectedCat,previousSession=sessionId;await syncAction(response,previousCat,previousSession);if(response.ui_action==='new_observation'){clearStream();message('user',text,response.caregiver_name);}if(response.cat_id&&selectedCat!==response.cat_id){if(subjectConfirmed&&sessionId&&response.session_id!==sessionId){clearStream();message('user',text,people.find(p=>p.caregiver_id===caregiverId)?.name);}selectedCat=response.cat_id;}sessionId=response.session_id;eventId=response.event_id;if(!eventId)clearRecord();subjectConfirmed=Boolean(response.cat_id);if(response.cat_id){write(sessionKey(response.cat_id),sessionId);write('catnanny.pendingSession',null);}else write('catnanny.pendingSession',sessionId);renderProfiles();retryPayload=null;$('message-input').value='';assistant(response,true);await requestedView(response);try{await refreshRecord();}catch{error('Conversation saved. Click Refresh to reload the record panel.');}}catch(e){if(e.status===409){retryPayload=null;error('The conversation changed. Reload it, or start a new observation for a separate episode.');}else error(`${e.message} Your input is kept; you can retry.`);}finally{setBusy(false);$('message-input').focus();}});
  $('message-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&!busy){e.preventDefault();$('chat-form').requestSubmit();}});
  for(const button of document.querySelectorAll('[data-example]'))button.addEventListener('click',()=>{if(busy)return;cancelAutoSend();const cat=profiles.find(c=>c.cat_id===selectedCat);$('message-input').value=button.dataset.example.replace('Mochi',cat?.name||'Mochi');$('message-input').focus();});
  $('new-conversation').addEventListener('click',()=>{if(busy)return;if(sessionId&&!confirm('Start a separate observation? Existing records stay in the care log.'))return;if(selectedCat)write(sessionKey(selectedCat),null);write('catnanny.pendingSession',null);sessionId=null;clearStream();$('message-input').value='';renderProfiles();$('message-input').focus();});
  $('caregiver-select').addEventListener('change',()=>write('catnanny.caregiver',$('caregiver-select').value));
  $('refresh-photos').addEventListener('click',()=>refreshRecord().catch(()=>error('Could not refresh photos. Please retry.')));
  window.addEventListener('storage',e=>{if(e.key==='catnanny.photo-uploaded'){try{if(JSON.parse(e.newValue)?.eventId===eventId)refreshRecord().catch(()=>{});}catch{}}});
  window.addEventListener('focus',()=>refreshRecord().catch(()=>{}));document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshRecord().catch(()=>{});});window.addEventListener('message',e=>{if(e.origin===location.origin&&e.data?.type==='catnanny:photo-uploaded'&&e.data.eventId===eventId)refreshRecord().catch(()=>{});});
  function table(items){const wrapper=node('div','table-scroll'),t=node('table','care-table'),head=node('thead'),header=node('tr');for(const title of ['Time','Observation / symptoms','Caregiver','Status','Photos'])header.append(node('th',null,title));head.append(header);t.append(head);const body=node('tbody');for(const item of items){const row=node('tr');row.append(node('td',null,time(item.time||item.occurred_at)));const symptoms=node('td');symptoms.append(node('strong',null,types[item.type||item.event_type]||item.type||item.event_type));for(const [key,value]of Object.entries(item.details)){if(labels[key])symptoms.append(node('div','muted',`${labels[key]}: ${format(value)}`));}const photos=node('td');const grid=node('div','photo-grid');photoGrid(grid,item.photos);if(!item.photos.length)grid.append(node('span','muted','No photo'));photos.append(grid);row.append(symptoms,node('td',null,item.reporter||'Not recorded'),node('td',null,item.status==='completed'?'Complete':item.status==='legacy'?'Logged':'Needs detail'),photos);body.append(row);}if(!items.length){const row=node('tr'),cell=node('td','muted','No observations in this period.');cell.colSpan=5;row.append(cell);body.append(row);}t.append(body);wrapper.append(t);return wrapper;}
  async function showReport(){latestReport=null;$('report-download').disabled=true;$('report-html').disabled=true;if(!selectedCat)return;if(!$('report-dialog').open)$('report-dialog').showModal();const run=++reportRun,cat=selectedCat,catName=profiles.find(c=>c.cat_id===cat)?.name||'Cat';$('report-title').textContent=`${catName} · Last ${$('report-days').value} days`;$('report-body').textContent='Preparing your requested report…';$('report-download').disabled=true;$('report-html').disabled=true;const end=new Date(),start=new Date(end.getTime()-Number($('report-days').value)*86400000);try{const report=await api('/reports/vet-summary?'+new URLSearchParams({cat_id:cat,start:start.toISOString(),end:end.toISOString()}));if(run!==reportRun||cat!==selectedCat)return;latestReport=report;$('report-body').replaceChildren(node('p','muted',`${report.counts.total_events} observation(s) for ${report.cat} · ${time(report.start)} – ${time(report.end)}`),table(report.timeline),node('p','muted','Times use the observation time when supplied; otherwise the original logged time. Observations only; not a diagnosis. Contact a veterinarian for medical advice.'));$('report-download').disabled=false;$('report-html').disabled=false;return report;}catch{if(run===reportRun)$('report-body').textContent='Could not load the report. Close and try again.';}}
  for(const id of ['report-open','report-mobile'])$(id).addEventListener('click',showReport);$('report-days').addEventListener('change',()=>{if($('report-dialog').open)showReport();});$('report-close').addEventListener('click',()=>{$('report-dialog').close();++reportRun;});
  function download(blob,name){const url=URL.createObjectURL(blob),a=node('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  $('report-download').addEventListener('click',()=>{if(latestReport)download(new Blob([JSON.stringify(latestReport,null,2)],{type:'application/json'}),'cat-nanny-care-report.json');});
  $('report-html').addEventListener('click',async()=>{if(!latestReport)return;$('report-html').disabled=true;$('report-html').textContent='Embedding photos…';$('report-days').disabled=true;try{const doc=document.implementation.createHTMLDocument(`${latestReport.cat} — Care report`);doc.documentElement.lang='en';const style=doc.createElement('style');style.textContent='body{font:14px/1.5 system-ui;margin:35px;color:#273d35}table{border-collapse:collapse;width:100%}th,td{border:1px solid #d9dfd4;padding:12px;text-align:left;vertical-align:top}img{width:130px;max-height:160px;object-fit:contain;margin:3px}.muted{font-size:12px;color:#657365}h1{font-size:25px}a{color:inherit}';doc.head.append(style);const heading=doc.createElement('h1');heading.textContent=`${latestReport.cat} — Care report`;doc.body.append(heading);for(const child of $('report-body').children)doc.body.append(child.cloneNode(true));for(const img of doc.querySelectorAll('img')){const response=await fetch(img.src);if(!response.ok)throw new Error('Could not embed a photo. Please retry.');const blob=await response.blob();img.src=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(blob);});img.removeAttribute('loading');const parent=img.parentElement;if(parent?.tagName==='A')parent.replaceWith(img);}download(new Blob(['<!doctype html>'+doc.documentElement.outerHTML],{type:'text/html'}),'cat-nanny-care-report.html');}catch{alert('Report download failed. Please check the photo connection and retry.');}finally{$('report-days').disabled=false;$('report-html').disabled=false;$('report-html').textContent='Download report with photos';}});
  async function showHistory(more=false){if(!selectedCat)return;if(!$('history-dialog').open)$('history-dialog').showModal();const cat=selectedCat;$('history-title').textContent=`${profiles.find(c=>c.cat_id===cat)?.name||'Cat'} · Care log`;if(!more){historyOffset=0;$('history-body').replaceChildren();}const offset=historyOffset;$('history-more').disabled=true;try{const page=await api(`/events?cat_id=${encodeURIComponent(cat)}&limit=50&offset=${offset}`);if(selectedCat!==cat)return;if(!more)$('history-body').append(node('p','muted',`${page.total} observation(s). Each row is a separate event; follow-up answers update the same row.`));$('history-body').append(table(page.items));historyOffset+=page.items.length;$('history-more').hidden=historyOffset>=page.total;}catch{$('history-body').textContent='Could not load the care log.';}finally{$('history-more').disabled=false;}}
  for(const id of ['history-open','history-mobile'])$(id).addEventListener('click',()=>showHistory());$('history-more').addEventListener('click',()=>showHistory(true));$('history-close').addEventListener('click',()=>$('history-dialog').close());
  function profileDialog(kind){if(busy)return;profileKind=kind;$('profile-title').textContent=kind==='cat'?'Add a companion':'Add caregiver';$('profile-sex-row').hidden=kind!=='cat';$('profile-name').value='';$('profile-sex').value='';$('profile-error').hidden=true;$('profile-dialog').showModal();$('profile-name').focus();}
  $('add-cat').addEventListener('click',()=>profileDialog('cat'));$('add-caregiver').addEventListener('click',()=>profileDialog('caregiver'));$('profile-cancel').addEventListener('click',()=>$('profile-dialog').close());
  function renderPeople(preferred){$('caregiver-select').replaceChildren();for(const p of people){const option=node('option',null,p.name);option.value=p.caregiver_id;$('caregiver-select').append(option);}if(people.some(p=>p.caregiver_id===preferred))$('caregiver-select').value=preferred;}
  $('profile-form').addEventListener('submit',async e=>{e.preventDefault();const name=$('profile-name').value.trim();if(!name)return;$('profile-save').disabled=true;try{const body={name};if(profileKind==='cat'&&$('profile-sex').value)body.sex=$('profile-sex').value;const data=await post(profileKind==='cat'?'/cats':'/caregivers',body);$('profile-dialog').close();if(profileKind==='cat'){profiles=await api('/cats');await selectCat(data.cat_id,true);}else{people=await api('/caregivers');renderPeople(data.caregiver_id);write('catnanny.caregiver',data.caregiver_id);}}catch(e){$('profile-error').textContent=e.message;$('profile-error').hidden=false;}finally{$('profile-save').disabled=false;}});
  async function init(){setBusy(true);try{const [catList,caregiverList,c]=await Promise.all([api('/cats'),api('/caregivers'),api('/capabilities')]);profiles=catList;people=caregiverList;const stored=read('catnanny.selectedCat');selectedCat=profiles.some(c=>c.cat_id===stored)?stored:profiles[0]?.cat_id;renderProfiles();renderPeople(read('catnanny.caregiver'));$('mode').textContent=c.extraction_provider==='openai'?(c.ai_configured?'Live AI mode':'AI needs configuration'):'Offline simulation';const pending=read('catnanny.pendingSession');const id=pending||read(sessionKey(selectedCat))||read('catnanny.activeSession');if(id){try{await restore(id);if(sessionId&&subjectConfirmed){write(sessionKey(selectedCat),sessionId);write('catnanny.activeSession',null);}}catch(e){if(e.status===404){sessionId=null;write('catnanny.pendingSession',null);}else throw e;}}}catch(e){error('Unable to connect. Refresh this page when the backend is available.');$('mode').textContent='Connection unavailable';}finally{setBusy(false);}}
  renderAudio();if(!audioSupported)$('audio-status').textContent='This browser cannot read replies aloud. Text replies remain available.';
  init();
})();
