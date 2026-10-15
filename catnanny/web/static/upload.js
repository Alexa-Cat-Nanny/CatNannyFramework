(() => {
  const $=(id)=>document.getElementById(id);
  const eventId=new URLSearchParams(location.search).get('event_id');
  let previewUrl=null, validEvent=false;
  function feedback(text,isError=false) { $('upload-feedback').textContent=text; $('upload-feedback').className=`notice${isError?' error':''}`; $('upload-feedback').hidden=false; }
  async function init() {
    if(!eventId) { feedback('This link has no observation. Open the photo link from your conversation.',true); return; }
    try { const response=await fetch(`/events/${encodeURIComponent(eventId)}`); if(!response.ok)throw new Error(); const event=await response.json(); $('upload-event').textContent=`${event.cat_name} · ${event.event_type==='vomit'?'Vomiting':'Appetite'} · ${new Date(event.occurred_at).toLocaleString('en-US')}`; validEvent=true; $('photo-input').disabled=false; }
    catch { feedback('Observation not found, or the service is unavailable. Return to the conversation and reopen the link.',true); }
  }
  $('photo-input').addEventListener('change',()=>{
    const file=$('photo-input').files[0]; $('upload-submit').disabled=true; $('upload-feedback').hidden=true; $('photo-preview').hidden=true;
    if(previewUrl) URL.revokeObjectURL(previewUrl);
    if(!file)return;
    if(!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size>8*1024*1024 || file.size===0) { feedback('Choose a JPEG, PNG, or WebP image up to 8 MB.',true); return; }
    previewUrl=URL.createObjectURL(file); $('photo-preview').src=previewUrl; $('photo-preview').hidden=false; $('file-name').textContent=file.name; $('upload-submit').disabled=!validEvent;
  });
  $('upload-form').addEventListener('submit',async(e)=>{
    e.preventDefault(); const file=$('photo-input').files[0]; if(!validEvent||!file)return;
    $('upload-submit').disabled=true; $('photo-input').disabled=true; $('upload-submit').textContent='Uploading…';
    const form=new FormData(); form.append('event_id',eventId); form.append('photo',file);
    try { const response=await fetch('/photos/upload',{method:'POST',body:form}); const data=await response.json(); if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Upload did not complete. Please retry.'); feedback('Photo uploaded and attached to this observation. Return to the conversation to view it.'); try { localStorage.setItem('catnanny.photo-uploaded',JSON.stringify({eventId,photoId:data.photo?.photo_id,at:Date.now()})); } catch {} try { if(window.opener) window.opener.postMessage({type:'catnanny:photo-uploaded',eventId},location.origin); } catch {} $('upload-submit').textContent='Uploaded'; $('photo-input').value=''; }
    catch(error) { feedback(error.message||'Upload did not complete. Please try again.',true); $('upload-submit').disabled=false; $('upload-submit').textContent='Retry upload'; }
    finally { $('photo-input').disabled=false; }
  });
  init();
})();
