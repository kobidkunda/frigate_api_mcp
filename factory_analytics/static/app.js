let appTimezone = 'UTC';

async function api(url, options = {}) { const res = await fetch(url, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options }); if (!res.ok) { const text = await res.text(); throw new Error(text || `Request failed: ${res.status}`);} return await res.json(); }
function fmtTs(ts){ if(!ts) return ''; try { const d = new Date(ts); return new Intl.DateTimeFormat('en-GB', { timeZone: appTimezone, year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false }).format(d); } catch(_) { return ts; } }
function fmtSec(sec){ sec=Number(sec||0); const h=Math.floor(sec/3600); const m=Math.floor((sec%3600)/60); return `${h}h ${m}m`; }
async function loadSettings(){ const data=await api('/api/settings'); appTimezone = data.timezone || 'UTC'; const form=document.getElementById('settingsForm'); if(form){ Object.entries(data).forEach(([k,v])=>{ const field=form.elements.namedItem(k); if(!field) return; field.value=typeof v==='boolean'?String(v):v;}); } }
async function saveSettings(ev){ ev.preventDefault(); const fd=new FormData(ev.target); const values=Object.fromEntries(fd.entries()); values.frigate_verify_tls = values.frigate_verify_tls === 'true'; values.scheduler_enabled = values.scheduler_enabled === 'true'; values.ollama_enabled = values.ollama_enabled === 'true'; values.analysis_interval_seconds = Number(values.analysis_interval_seconds || 300); values.ollama_timeout_sec = Number(values.ollama_timeout_sec || 120); await api('/api/settings',{method:'PUT',body:JSON.stringify({values})}); await refreshAll(); alert('Settings saved'); }

async function testOllamaVision(){
  const out = document.getElementById('ollama-test-result');
  if(out) out.textContent = 'Testing Ollama vision...';
  try {
    const result = await api('/api/settings/ollama/test', { method: 'POST' });
    if(out) out.textContent = result.ok
      ? `OK: ${result.model} on ${result.camera} -> ${result.label} (${Number(result.confidence || 0).toFixed(2)})`
      : `Failed: ${result.message}`;
  } catch (err) {
    if(out) out.textContent = `Failed: ${err.message || String(err)}`;
  }
}
async function loadHealth(){ 
  const data=await api('/api/health'); 
  const el=document.getElementById('healthCards'); 
  if(!el) return; 
  const cards=[ 
    ['Application', data.database.ok, data.database.message, 'settings_applications'], 
    ['Database', data.database.ok, data.database.message, 'database'], 
    ['Frigate', data.frigate.ok, data.frigate.version || data.frigate.message || '', 'videocam'], 
    ['Ollama', data.ollama.ok, (data.ollama.models || []).join(', ') || data.ollama.message || '', 'psychology'] 
  ]; 
  el.innerHTML = cards.map(([name,ok,msg,icon]) => `
    <div class="bg-surface-container p-3 flex flex-col items-center justify-center gap-1 rounded-lg">
      <div class="w-2 h-2 rounded-full ${ok?'bg-tertiary shadow-[0_0_8px_#00e475]':'bg-error animate-pulse shadow-[0_0_8px_#ffb4ab]'}"></div>
      <span class="font-label text-[10px] text-outline uppercase">${name}</span>
      <span class="font-headline font-bold text-sm ${ok?'':'text-error'}">${ok?'Healthy':'Issue'}</span>
      <div class="text-[8px] text-outline truncate w-full text-center" title="${msg}">${msg || ''}</div>
    </div>`).join(''); 
}
async function syncCameras(){ await api('/api/frigate/cameras/sync'); await loadCameras(); }
async function loadCameras(){ 
  const cameras=await api('/api/cameras'); 
  const el=document.getElementById('cameraTable'); 
  if(!el) return; 
  el.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-surface-container-high/30">
            <th class="p-4 font-label text-[10px] uppercase text-outline tracking-widest">ID</th>
            <th class="p-4 font-label text-[10px] uppercase text-outline tracking-widest">Name</th>
            <th class="p-4 font-label text-[10px] uppercase text-outline tracking-widest">Source</th>
            <th class="p-4 font-label text-[10px] uppercase text-outline tracking-widest text-center">State</th>
            <th class="p-4 font-label text-[10px] uppercase text-outline tracking-widest text-center">Interval</th>
            <th class="p-4 font-label text-[10px] uppercase text-outline tracking-widest">Status</th>
            <th class="p-4 font-label text-[10px] uppercase text-outline tracking-widest text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/10">
          ${cameras.map(c=>`
            <tr class="hover:bg-surface-container transition-colors group">
              <td class="p-4 text-xs font-label text-primary">#${c.id}</td>
              <td class="p-4">
                <input value="${c.name}" id="camera-name-${c.id}" class="bg-surface-container-lowest border-none text-sm p-1.5 rounded focus:ring-1 focus:ring-primary w-full font-semibold" />
              </td>
              <td class="p-4 text-xs font-label text-outline truncate max-w-[120px]" title="${c.frigate_name}">${c.frigate_name}</td>
              <td class="p-4 text-center">
                <label class="relative inline-flex items-center cursor-pointer justify-center">
                  <input type="checkbox" ${c.enabled ? 'checked' : ''} id="camera-enabled-${c.id}" class="sr-only peer">
                  <div class="w-9 h-5 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </td>
              <td class="p-4">
                <input type="number" min="30" value="${c.interval_seconds}" id="camera-interval-${c.id}" class="bg-surface-container-lowest border-none text-xs w-16 px-2 py-1 text-center rounded mx-auto block" />
              </td>
              <td class="p-4">
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-2">
                    <span class="w-1.5 h-1.5 rounded-full ${c.last_status === 'ok' ? 'bg-tertiary' : 'bg-error'}"></span>
                    <span class="text-[10px] uppercase font-bold ${c.last_status === 'ok' ? 'text-tertiary' : 'text-error'}">${c.last_status || 'Never Run'}</span>
                  </div>
                  <div class="text-[9px] text-outline font-label">${fmtTs(c.last_run_at)}</div>
                  <div id="camera-test-status-${c.id}" class="text-[9px] italic text-primary"></div>
                </div>
              </td>
              <td class="p-4 text-right">
                <div class="flex justify-end gap-1">
                  <button onclick="saveCamera(${c.id})" class="text-primary p-1.5 hover:bg-surface-bright rounded transition-colors" title="Save">
                    <span class="material-symbols-outlined text-sm">save</span>
                  </button>
                  <button onclick="testCameraRow(${c.id})" class="text-outline p-1.5 hover:bg-surface-bright rounded transition-colors" title="Test">
                    <span class="material-symbols-outlined text-sm">analytics</span>
                  </button>
                  <button onclick="deleteCamera(${c.id})" class="text-error/60 p-1.5 hover:bg-error-container/20 rounded transition-colors" title="Delete">
                    <span class="material-symbols-outlined text-sm">delete</span>
                  </button>
                </div>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  
  try{ 
    const data = await api('/api/frigate/cameras'); 
    const sel=document.getElementById('frigate-camera-select'); 
    if(sel) sel.innerHTML = `<option value="">Select Frigate Camera</option>` + (data.cameras||[]).map(n=>`<option value="${n}">${n}</option>`).join(''); 
  }catch(_){ 
    const sel=document.getElementById('frigate-camera-select'); 
    if(sel) sel.innerHTML = `<option value="">(Frigate unavailable)</option>`; 
  }
}
async function loadGroups(){ 
  const el=document.getElementById('groupTable'); 
  if(!el) return; 
  let groups, cameras; 
  try { 
    groups = await api('/api/groups'); 
    cameras = await api('/api/cameras'); 
  } catch(e) { 
    el.innerHTML = '<div class="p-4 text-error font-label text-xs uppercase">Failed to load groups</div>'; 
    return; 
  } 
  const options = cameras.map(c=>`<option value="${c.id}">${c.name || c.frigate_name}</option>`).join(''); 
  el.innerHTML = groups.map(g=>`
    <div class="bg-surface-container p-4 flex items-center justify-between group hover:bg-surface-container-highest transition-colors rounded-lg border border-outline-variant/5 mb-3">
      <div class="flex flex-col gap-1">
        <div class="flex items-center gap-2">
          <span class="font-label text-[10px] text-primary uppercase">${g.group_type}</span>
          <span class="text-[9px] text-outline font-mono">#${g.id}</span>
        </div>
        <span class="font-headline font-bold text-sm">${g.name}</span>
        <div class="flex items-center gap-2 mt-1">
          <span class="text-[9px] text-outline uppercase font-label">Interval:</span>
          <input id="interval-${g.id}" value="${g.interval_seconds || 300}" onchange="updateGroupInterval(${g.id})" class="bg-surface-container-lowest border-none text-[9px] w-12 px-1 rounded text-center focus:ring-1 focus:ring-primary" />
        </div>
      </div>
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <select id="group-camera-${g.id}" class="bg-surface-container-lowest border-none text-[10px] p-1.5 rounded focus:ring-0 w-32">${options}</select>
          <button onclick="addCameraToGroup(${g.id})" class="bg-primary/10 text-primary p-1.5 rounded hover:bg-primary/20 transition-colors" title="Add Member">
            <span class="material-symbols-outlined text-sm">person_add</span>
          </button>
        </div>
        <button onclick="runGroup(${g.id})" class="machined-gradient text-on-primary-fixed p-2 rounded-full hover:scale-110 active:scale-95 transition-all shadow-lg" title="Run Analysis">
          <span class="material-symbols-outlined text-sm">play_arrow</span>
        </button>
      </div>
    </div>`).join('') || '<div class="p-8 text-center text-outline font-label text-xs uppercase">No groups defined</div>'; 
}
async function updateGroupInterval(groupId) {
    const intervalInput = document.getElementById(`interval-${groupId}`);
    const interval = parseInt(intervalInput.value);
    if (isNaN(interval) || interval < 1) {
        alert('Interval must be a positive number');
        return;
    }
    
    try {
        await api(`/api/groups/${groupId}`, {
            method: 'PUT',
            body: JSON.stringify({ interval_seconds: interval })
        });
        alert('Group interval updated');
    } catch (e) {
        alert('Failed to update interval');
    }
}

async function addGroup(){ const group_type=document.getElementById('group-type').value.trim(); const name=document.getElementById('group-name').value.trim(); const interval=parseInt(document.getElementById('group-interval').value); if(!group_type || !name){ alert('Enter group type and name'); return; } if(isNaN(interval) || interval < 1){ alert('Interval must be positive'); return; } await api('/api/groups',{method:'POST',body:JSON.stringify({group_type,name,interval_seconds:interval})}); await loadGroups(); }
async function addCameraToGroup(groupId){ const sel=document.getElementById(`group-camera-${groupId}`); await api(`/api/groups/${groupId}/cameras`,{method:'POST',body:JSON.stringify({camera_id:Number(sel.value)})}); alert('Camera added to group'); }
async function runGroup(groupId){ const res = await api(`/api/groups/${groupId}/run`,{method:'POST'}); alert(`Group OK: ${res.label} (${Number(res.confidence||0).toFixed(2)})`); }
async function saveCamera(id){ const payload={ name:document.getElementById(`camera-name-${id}`).value, enabled:document.getElementById(`camera-enabled-${id}`).checked, interval_seconds:Number(document.getElementById(`camera-interval-${id}`).value || 300)}; await api(`/api/cameras/${id}`,{method:'PUT',body:JSON.stringify(payload)}); await loadCameras(); }
async function runCamera(id){ await api(`/api/cameras/${id}/run`,{method:'POST'}); setTimeout(refreshAll,1000); }
async function addCamera(){ const sel=document.getElementById('frigate-camera-select'); const manual=document.getElementById('frigate-manual').value.trim(); const frigate_name = manual || (sel && sel.value) || ''; if(!frigate_name){ alert('Choose a Frigate camera or enter one manually'); return; } const payload={ frigate_name, name:document.getElementById('camera-display-name').value.trim()||undefined, enabled:document.getElementById('camera-enabled-new').checked, interval_seconds:Number(document.getElementById('camera-interval-new').value||300)}; await api('/api/cameras',{method:'POST',body:JSON.stringify(payload)}); // Update ollama enablement setting globally if user changed it
  const ollamaEnabled = (document.getElementById('ollama-enabled-select')?.value || 'true') === 'true'; await api('/api/settings',{method:'PUT',body:JSON.stringify({values:{ollama_enabled: ollamaEnabled}})}); await loadCameras(); }
async function testNewCamera(){ const sel=document.getElementById('frigate-camera-select'); const manual=document.getElementById('frigate-manual').value.trim(); const frigate_name = manual || (sel && sel.value) || ''; const statusEl=document.getElementById('new-camera-test-status'); if(!frigate_name){ if(statusEl) statusEl.textContent='Choose a Frigate camera or enter one manually'; return; } try{ if(statusEl){ statusEl.textContent='Testing...'; } const res=await api('/api/cameras/test',{method:'POST',body:JSON.stringify({frigate_name})}); if(statusEl){ statusEl.textContent = res.ok ? `OK: ${res.label} (${Number(res.confidence||0).toFixed(2)})` : `Failed: ${res.error||'unknown error'}`; } } catch(err){ if(statusEl){ statusEl.textContent = `Failed: ${err.message||String(err)}`; } }
}
async function testCameraRow(id){ const statusEl=document.getElementById(`camera-test-status-${id}`); try{ if(statusEl){ statusEl.textContent='Testing...'; }
  // Try probe endpoint first
  const resp = await fetch('/api/cameras/test',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({camera_id:id}) });
  if(resp.status === 405 || resp.status === 404){
    // Fallback: schedule a job as a test and show job status
    const job = await api(`/api/cameras/${id}/run`,{method:'POST'});
    if(statusEl){ statusEl.textContent=`Job #${job.id} queued...`; }
    pollJob(job.id, statusEl);
    return;
  }
  if(!resp.ok){ const text = await resp.text(); throw new Error(text || `HTTP ${resp.status}`); }
  const res = await resp.json();
  if(statusEl){ statusEl.textContent = res.ok ? `OK: ${res.label} (${Number(res.confidence||0).toFixed(2)})` : `Failed: ${res.error||'unknown error'}`; }
} catch(err){ if(statusEl){ statusEl.textContent = `Failed: ${err.message||String(err)}`; } }
}

async function pollJob(jobId, statusEl, attempts=0){
  try{
    const job = await api(`/api/jobs/${jobId}`);
    if(job.status === 'pending' || job.status === 'running'){
      if(statusEl){ statusEl.textContent = `Job #${job.id} ${job.status}...`; }
      if(attempts < 60){ setTimeout(() => pollJob(jobId, statusEl, attempts+1), 1000); }
      return;
    }
    if(job.status === 'success'){
      if(statusEl){ statusEl.textContent = `Job #${job.id} success`; }
      // refresh to update last_run/status
      setTimeout(refreshAll, 500);
      return;
    }
    if(statusEl){ statusEl.textContent = `Job #${job.id} failed: ${job.error || 'unknown'}`; }
  }catch(err){ if(statusEl){ statusEl.textContent = `Job check failed: ${err.message||String(err)}`; } }
}
async function deleteCamera(id){
  if(!confirm('Delete this camera? This will remove related jobs and segments.')) return;
  // Try DELETE first
  let resp = await fetch(`/api/cameras/${id}`,{method:'DELETE'});
  if(resp.status === 405){
    // Fallback to POST /delete for environments where DELETE is blocked
    resp = await fetch(`/api/cameras/${id}/delete`,{method:'POST'});
  }
  if(!resp.ok){ const text = await resp.text(); alert(text || `HTTP ${resp.status}`); return; }
  const res = await resp.json();
  if(!res.deleted){ alert(res.error ? `Delete failed: ${res.error}` : 'Delete did not remove any rows'); }
  await loadCameras();
}
async function loadJobs(){ const jobs=await api('/api/jobs'); const el = document.getElementById('jobsTable'); if(!el) return; el.innerHTML = `<table><thead><tr><th>ID</th><th>Camera</th><th>Status</th><th>Type</th><th>Scheduled</th><th>Finished</th><th>Error</th></tr></thead><tbody>${jobs.map(j=>`<tr><td>${j.id}</td><td>${j.camera_name || j.camera_id}</td><td>${j.status}</td><td>${j.job_type}</td><td>${fmtTs(j.scheduled_for)}</td><td>${fmtTs(j.finished_at)}</td><td>${j.error || ''}</td></tr>`).join('')}</tbody></table>`; }
async function loadSegments(){ const segments=await api('/api/history/segments'); const el = document.getElementById('segmentsTable'); if(!el) return; el.innerHTML = `<table><thead><tr><th>ID</th><th>Camera</th><th>Label</th><th>Confidence</th><th>Window</th><th>Evidence</th><th>Review</th></tr></thead><tbody>${segments.map(s=>`<tr><td>${s.id}</td><td>${s.camera_name}</td><td>${s.reviewed_label || s.label}</td><td>${Number(s.confidence || 0).toFixed(2)}</td><td>${fmtTs(s.start_ts)}<div class="small">${fmtTs(s.end_ts)}</div></td><td>${s.evidence_path ? `<img src="/${s.evidence_path}" alt="evidence" loading="lazy" style="max-width:160px;max-height:120px;border:1px solid #222;border-radius:4px" onerror="this.replaceWith(document.createTextNode('no image'))" />` : ''}</td><td><div class="inline-actions"><button class="secondary" onclick="reviewSegment(${s.id}, 'working')">Mark working</button><button class="secondary" onclick="reviewSegment(${s.id}, 'idle')">Mark idle</button><button class="secondary" onclick="reviewSegment(${s.id}, 'sleeping')">Mark sleeping</button></div></td></tr>`).join('')}</tbody></table>`; }
async function reviewSegment(id,label){ await api(`/api/review/${id}`,{method:'POST',body:JSON.stringify({reviewed_label:label,review_note:'manual review from GUI'})}); await loadSegments(); }
async function loadChart(){ const rows=await api('/api/charts/daily?days=7'); const canvas=document.getElementById('chartCanvas'); if(!canvas) return; const ctx=canvas.getContext('2d'); ctx.clearRect(0,0,canvas.width,canvas.height); const pad=40; const width=canvas.width - pad*2; const height=canvas.height - pad*2; const values=rows.flatMap(r=>[r.working_seconds,r.idle_seconds,r.sleeping_seconds]); const max=Math.max(1,...values); ctx.strokeStyle='#7082c3'; ctx.beginPath(); ctx.moveTo(pad,pad); ctx.lineTo(pad,pad+height); ctx.lineTo(pad+width,pad+height); ctx.stroke(); const barWidth=width/Math.max(1,rows.length*4); rows.forEach((row,i)=>{ const baseX=pad+i*barWidth*4+barWidth; const bars=[row.working_seconds,row.idle_seconds,row.sleeping_seconds]; const colors=['#3ad48f','#ffcc66','#ff5d73']; bars.forEach((val,idx)=>{ const h=(val/max)*height; ctx.fillStyle=colors[idx]; ctx.fillRect(baseX+idx*barWidth,pad+height-h,barWidth-2,h);}); ctx.fillStyle='#cbd5ff'; ctx.font='10px sans-serif'; ctx.fillText(row.day.slice(5), baseX, pad+height+12); }); }
async function loadReport(){ 
  const today=new Date().toISOString().slice(0,10); 
  const report=await api(`/api/reports/daily?day=${today}`); 
  const t=report.totals || {}; 
  const el = document.getElementById('reportView'); 
  if(!el) return; 
  el.innerHTML = `
    <div class="grid grid-cols-2 gap-4 w-full">
      <div class="p-2 bg-surface-container-low rounded">
        <span class="block text-[10px] text-tertiary uppercase font-label">Working</span>
        <span class="text-lg font-headline font-bold">${fmtSec(t.working_seconds)}</span>
      </div>
      <div class="p-2 bg-surface-container-low rounded">
        <span class="block text-[10px] text-outline uppercase font-label">Idle</span>
        <span class="text-lg font-headline font-bold">${fmtSec(t.idle_seconds)}</span>
      </div>
      <div class="p-2 bg-surface-container-low rounded">
        <span class="block text-[10px] text-secondary uppercase font-label">Sleeping</span>
        <span class="text-lg font-headline font-bold">${fmtSec(t.sleeping_seconds)}</span>
      </div>
      <div class="p-2 bg-surface-container-low rounded">
        <span class="block text-[10px] text-error uppercase font-label">Stopped</span>
        <span class="text-lg font-headline font-bold">${fmtSec(t.stopped_seconds || t.uncertain_seconds)}</span>
      </div>
    </div>
    <div class="mt-4 pt-2 border-t border-outline-variant/10">
      <span class="block text-[10px] text-outline uppercase font-label mb-2">Segment Velocity</span>
      <div class="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
        <div class="bg-primary h-full" style="width: ${Math.min(100, (report.recent_segments?.length || 0) * 5)}%;"></div>
      </div>
      <div class="text-[8px] text-outline mt-1 uppercase font-label">${(report.recent_segments || []).length} active events detected</div>
    </div>
  `; 
}
async function loadLog(name){ const data=await api(`/api/logs/tail?name=${name}`); const el = document.getElementById('logView'); if(!el) return; el.textContent = data.content || ''; }
function el(id){ return document.getElementById(id); }
async function refreshAll(){
  try{
    const tasks=[];
    if(el('settingsForm')) tasks.push(loadSettings());
    if(el('healthCards')) tasks.push(loadHealth());
    if(el('cameraTable')) tasks.push(loadCameras());
    if(el('groupTable')) tasks.push(loadGroups());
    if(el('jobsTable')) tasks.push(loadJobs());
    if(el('segmentsTable')) tasks.push(loadSegments());
    if(el('chartCanvas')) tasks.push(loadChart());
    if(el('reportView')) tasks.push(loadReport());
    await Promise.all(tasks);
    if(el('logView')) await loadLog('worker');
  } catch(err){ console.error(err); alert(err.message || String(err)); }
}

function initApp(){
  const form = el('settingsForm');
  if(form && form.addEventListener){ form.addEventListener('submit', saveSettings); }
  const testBtn = el('testOllamaBtn');
  if(testBtn && testBtn.addEventListener){ testBtn.addEventListener('click', testOllamaVision); }
  refreshAll();
}

if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initApp); else initApp();

// Theme manager with localStorage and system fallback
(function(){
  const KEY = 'fa_theme';
  function applyTheme(theme){
    if(theme === 'light' || theme === 'dark'){ document.documentElement.setAttribute('data-theme', theme); }
    else { document.documentElement.removeAttribute('data-theme'); }
  }
  function initTheme(){
    try{ const stored = localStorage.getItem(KEY); applyTheme(stored || ''); }catch(_){/* ignore */}
    const toggle = document.getElementById('themeToggle');
    if(toggle){
      toggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        try{ localStorage.setItem(KEY, next); }catch(_){/* ignore */}
      });
    }
    const menuToggle = document.getElementById('menuToggle');
    const primaryNav = document.getElementById('primaryNav');
    if(menuToggle && primaryNav){
      menuToggle.addEventListener('click', () => {
        const open = primaryNav.classList.toggle('open');
        menuToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initTheme); else initTheme();
})();
