let processedPage = 1;

async function processedApi(url){
  const res = await fetch(url);
  if(!res.ok){ throw new Error(await res.text() || `Request failed: ${res.status}`); }
  return await res.json();
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
    el.innerHTML = `<table><thead><tr><th>ID</th><th>Camera</th><th>Status</th><th>Type</th><th>Finished</th><th>Error</th></tr></thead><tbody>${items.map(i=>`<tr><td>${i.id}</td><td>${i.camera_name||''}</td><td>${i.status||''}</td><td>${i.job_type||''}</td><td>${i.finished_at||i.started_at||i.scheduled_for||''}</td><td>${i.error||''}</td></tr>`).join('')}</tbody></table>`;
  } else {
    el.innerHTML = `<table><thead><tr><th>ID</th><th>Camera</th><th>Label</th><th>Confidence</th><th>Start</th><th>Evidence</th></tr></thead><tbody>${items.map(i=>`<tr><td>${i.id}</td><td>${i.camera_name||''}</td><td>${i.reviewed_label||i.label||''}</td><td>${Number(i.confidence||0).toFixed(2)}</td><td>${i.start_ts||''}</td><td>${i.evidence_path ? `<img src="/${i.evidence_path}" alt="evidence" style="max-width:100px;max-height:70px" />` : ''}</td></tr>`).join('')}</tbody></table>`;
  }
  document.getElementById('page-info').textContent = `Page ${data.page} · Total ${data.total}`;
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('processedFilterForm').addEventListener('submit', (ev) => { ev.preventDefault(); processedPage = 1; loadProcessedEvents(); });
  document.getElementById('page-prev').addEventListener('click', () => { if(processedPage > 1){ processedPage -= 1; loadProcessedEvents(); } });
  document.getElementById('page-next').addEventListener('click', () => { processedPage += 1; loadProcessedEvents(); });
  loadProcessedEvents();
});
