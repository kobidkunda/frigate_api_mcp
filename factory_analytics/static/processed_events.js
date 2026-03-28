let processedPage = 1;
let processedTimezone = 'UTC';

async function processedApi(url){
  const res = await fetch(url);
  if(!res.ok){ throw new Error(await res.text() || `Request failed: ${res.status}`); }
  return await res.json();
}

async function loadProcessedTimezone(){
  try{
    const settings = await processedApi('/api/settings');
    processedTimezone = settings.timezone || 'UTC';
  }catch(_){ processedTimezone = 'UTC'; }
}

function fmtProcessedTs(ts){
  if(!ts) return '';
  try{
    return new Intl.DateTimeFormat('en-GB', { timeZone: processedTimezone, year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false }).format(new Date(ts));
  }catch(_){ return ts; }
}

async function loadProcessedEvents(){
  const form = document.getElementById('processedFilterForm');
  const fd = new FormData(form);
  const params = new URLSearchParams();
  fd.forEach((v,k) => { if(v) params.append(k, v); });
  params.set('page', String(processedPage));
  params.set('page_size', '25');
  const view = fd.get('view') || 'jobs';
  const url = `/api/processed-events/${view}?` + params.toString();
  const data = await processedApi(url);
  const el = document.getElementById('processedEventsTable');
  const items = data.items || [];
  if(view === 'jobs'){
    el.innerHTML = `<table><thead><tr><th>ID</th><th>Camera</th><th>Status</th><th>Type</th><th>Finished</th><th>Error</th></tr></thead><tbody>${items.map(i=>`<tr><td>${i.id}</td><td>${i.camera_name||''}</td><td>${i.status||''}</td><td>${i.job_type||''}</td><td>${fmtProcessedTs(i.finished_at||i.started_at||i.scheduled_for)}</td><td>${i.error||''}</td></tr>`).join('')}</tbody></table>`;
  } else {
    const groupBadge = (i) => i.job_type === 'group_analysis' ? `<div class="history-group-badge">Group Result</div><div class="history-group-name">${i.group_type || 'group'}: ${i.group_name || 'unnamed group'}</div>` : '';
    const llmNotes = (i) => `${groupBadge(i)}<div class="history-llm-notes">${i.notes || ''}</div><div class="history-merge-meta">${i.raw_result?.included_cameras ? `Included: ${(i.raw_result.included_cameras || []).join(', ')}${(i.raw_result.missing_cameras || []).length ? ` | Missing: ${(i.raw_result.missing_cameras || []).join(', ')}` : ''}` : ''}</div>`;
    el.innerHTML = `<table><thead><tr><th>ID</th><th>Camera</th><th>Label</th><th>Confidence</th><th>Start</th><th>Evidence</th></tr></thead><tbody>${items.map(i=>`<tr><td>${i.id}</td><td>${i.camera_name||''}</td><td>${i.reviewed_label||i.label||''}${llmNotes(i)}</td><td>${Number(i.confidence||0).toFixed(2)}</td><td>${fmtProcessedTs(i.start_ts)}</td><td>${i.evidence_path ? `<img src="/${i.evidence_path}" alt="evidence" style="max-width:100px;max-height:70px" />` : ''}</td></tr>`).join('')}</tbody></table>`;
  }
  document.getElementById('page-info').textContent = `Page ${data.page} · Total ${data.total}`;
}

document.addEventListener('DOMContentLoaded', () => {
  loadProcessedTimezone().then(loadProcessedEvents);
  document.getElementById('processedFilterForm').addEventListener('submit', (ev) => { ev.preventDefault(); processedPage = 1; loadProcessedEvents(); });
  document.getElementById('page-prev').addEventListener('click', () => { if(processedPage > 1){ processedPage -= 1; loadProcessedEvents(); } });
  document.getElementById('page-next').addEventListener('click', () => { processedPage += 1; loadProcessedEvents(); });
});
