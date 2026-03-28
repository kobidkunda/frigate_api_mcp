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
async function loadHealth(){ const data=await api('/api/health'); const el=document.getElementById('healthCards'); if(!el) return; const cards=[ ['App', true, 'running'], ['Database', data.database.ok, data.database.message], ['Frigate', data.frigate.ok, data.frigate.version || data.frigate.message || ''], ['Ollama', data.ollama.ok, (data.ollama.models || []).join(', ') || data.ollama.message || ''] ]; el.innerHTML = cards.map(([name,ok,msg]) => `<div class="status-card"><div>${name}</div><div class="${ok?'ok':'bad'}">${ok?'Healthy':'Issue'}</div><div class="small">${msg || ''}</div></div>`).join(''); }
async function syncCameras(){ await api('/api/frigate/cameras/sync'); await loadCameras(); }
async function loadCameras(){ const cameras=await api('/api/cameras'); const el=document.getElementById('cameraTable'); if(!el) return; const addForm = `<div class="add-camera">
  <div class="inline-actions">
    <select id="frigate-camera-select"><option value="">Loading…</option></select>
    <input id="frigate-manual" placeholder="Manual Frigate Name (optional)" />
    <input id="camera-display-name" placeholder="Display Name (optional)" />
    <input id="camera-interval-new" type="number" min="30" value="300" />
    <label><input id="camera-enabled-new" type="checkbox" checked /> Enabled</label>
    <label><span>Vision Inference</span>
      <select id="ollama-enabled-select"><option value="true">Enabled</option><option value="false">Disabled</option></select>
    </label>
    <button class="secondary" onclick="testNewCamera()">Test</button>
    <button onclick="addCamera()">Add Camera</button>
  </div>
  <div class="small">Use Test to verify connectivity before saving</div>
  <div id="new-camera-test-status" class="small"></div>
</div>`;
  el.innerHTML = addForm + `<table><thead><tr><th>ID</th><th>Name</th><th>Frigate Name</th><th>Enabled</th><th>Interval</th><th>Status</th><th>Actions</th></tr></thead><tbody>${cameras.map(c=>`<tr><td>${c.id}</td><td><input value="${c.name}" id="camera-name-${c.id}" /></td><td>${c.frigate_name}</td><td><input type="checkbox" ${c.enabled ? 'checked' : ''} id="camera-enabled-${c.id}" /></td><td><input type="number" min="30" value="${c.interval_seconds}" id="camera-interval-${c.id}" /></td><td>${c.last_status || ''}<div class="small">${fmtTs(c.last_run_at)}</div><div id="camera-test-status-${c.id}" class="small"></div></td><td class="inline-actions"><button onclick="saveCamera(${c.id})">Save Camera</button><button class="secondary" onclick="testCameraRow(${c.id})">Test</button><button class="danger" onclick="deleteCamera(${c.id})">Delete</button></td></tr>`).join('')}</tbody></table>`;
  try{ const data = await api('/api/frigate/cameras'); const sel=document.getElementById('frigate-camera-select'); sel.innerHTML = `<option value="">Select Frigate Camera</option>` + (data.cameras||[]).map(n=>`<option value="${n}">${n}</option>`).join(''); }catch(_){ const sel=document.getElementById('frigate-camera-select'); if(sel) sel.innerHTML = `<option value="">(Frigate unavailable)</option>`; }
}
async function loadGroups(){ const el=document.getElementById('groupTable'); if(!el) return; let groups, cameras; try { groups = await api('/api/groups'); cameras = await api('/api/cameras'); } catch(e) { el.innerHTML = '<div class="error">Failed to load groups</div>'; return; } const options = cameras.map(c=>`<option value="${c.id}">${c.name}</option>`).join(''); el.innerHTML = `<div class="add-group"><div class="inline-actions"><input id="group-type" placeholder="machine or room" /><input id="group-name" placeholder="Group name" /><input id="group-interval" placeholder="Interval (s)" value="300" /><button onclick="addGroup()">Add Group</button></div></div><table><thead><tr><th>ID</th><th>Type</th><th>Name</th><th>Interval (s)</th><th>Cameras</th><th>Actions</th></tr></thead><tbody>${groups.map(g=>`<tr><td>${g.id}</td><td>${g.group_type}</td><td>${g.name}</td><td><input id="interval-${g.id}" value="${g.interval_seconds || 300}" onchange="updateGroupInterval(${g.id})" /></td><td><select id="group-camera-${g.id}">${options}</select></td><td class="inline-actions"><button onclick="addCameraToGroup(${g.id})">Add Camera</button><button class="secondary" onclick="runGroup(${g.id})">Run Group</button></td></tr>`).join('')}</tbody></table>`; }
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
async function loadReport(){ const today=new Date().toISOString().slice(0,10); const report=await api(`/api/reports/daily?day=${today}`); const t=report.totals || {}; const el = document.getElementById('reportView'); if(!el) return; el.innerHTML = `<div><strong>Date:</strong> ${report.day}</div><div><strong>Working:</strong> ${fmtSec(t.working_seconds)}</div><div><strong>Idle:</strong> ${fmtSec(t.idle_seconds)}</div><div><strong>Sleeping:</strong> ${fmtSec(t.sleeping_seconds)}</div><div><strong>Uncertain:</strong> ${fmtSec(t.uncertain_seconds)}</div><div><strong>Stopped:</strong> ${fmtSec(t.stopped_seconds)}</div><div class="small">Recent segments: ${(report.recent_segments || []).length}</div>`; }
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
