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
    el.innerHTML = `
      <table class="w-full text-left text-xs border-collapse">
        <thead>
          <tr class="bg-surface-container text-outline text-[10px] uppercase tracking-widest font-label border-b border-outline-variant/10">
            <th class="px-4 py-3">ID</th>
            <th class="px-4 py-3">Camera</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3">Type</th>
            <th class="px-4 py-3">Finished</th>
            <th class="px-4 py-3">Error</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/5">
          ${items.map(i=>`
            <tr class="hover:bg-surface-container-highest/20 transition-colors">
              <td class="px-4 py-4 text-primary font-mono">#JOB-${i.id}</td>
              <td class="px-4 py-4 font-medium">${i.camera_name||''}</td>
              <td class="px-4 py-4">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${i.status==='success'?'bg-tertiary/10 text-tertiary':(i.status==='failed'?'bg-error/10 text-error':'bg-outline/10 text-outline')}">${i.status||''}</span>
              </td>
              <td class="px-4 py-4 text-[10px] uppercase font-label text-outline">${i.job_type||''}</td>
              <td class="px-4 py-4 text-on-surface-variant">${fmtProcessedTs(i.finished_at||i.started_at||i.scheduled_for)}</td>
              <td class="px-4 py-4 text-error text-[10px] truncate max-w-[150px]" title="${i.error||''}">${i.error||''}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } else {
    el.innerHTML = `
      <table class="w-full text-left text-xs border-collapse">
        <thead>
          <tr class="bg-surface-container text-outline text-[10px] uppercase tracking-widest font-label border-b border-outline-variant/10">
            <th class="px-4 py-3">ID</th>
            <th class="px-4 py-3">Camera</th>
            <th class="px-4 py-3">Classification</th>
            <th class="px-4 py-3">Conf.</th>
            <th class="px-4 py-3">Start</th>
            <th class="px-4 py-3">Evidence</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/5">
          ${items.map(i=>`
            <tr class="hover:bg-surface-container-highest/20 transition-colors">
              <td class="px-4 py-4 text-primary font-mono">#SEG-${i.id}</td>
              <td class="px-4 py-4 font-medium">${i.camera_name||''}</td>
              <td class="px-4 py-4">
                <div class="font-bold capitalize">${i.reviewed_label||i.label||''}</div>
                <div class="text-[10px] text-outline line-clamp-1 truncate max-w-[200px]" title="${i.notes || ''}">${i.notes || ''}</div>
              </td>
              <td class="px-4 py-4 font-label font-bold text-tertiary">${Math.round((i.confidence||0)*100)}%</td>
              <td class="px-4 py-4 text-on-surface-variant">${fmtProcessedTs(i.start_ts)}</td>
              <td class="px-4 py-4">
                ${i.evidence_path ? `<img src="/${i.evidence_path}" alt="evidence" class="w-16 h-10 object-cover rounded border border-outline-variant/10" />` : '<span class="text-[10px] text-outline italic">No image</span>'}
              </td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }
  document.getElementById('page-info').textContent = `Page ${data.page} · Total ${data.total}`;
}

document.addEventListener('DOMContentLoaded', () => {
  loadProcessedTimezone().then(loadProcessedEvents);
  document.getElementById('processedFilterForm').addEventListener('submit', (ev) => { ev.preventDefault(); processedPage = 1; loadProcessedEvents(); });
  document.getElementById('page-prev').addEventListener('click', () => { if(processedPage > 1){ processedPage -= 1; loadProcessedEvents(); } });
  document.getElementById('page-next').addEventListener('click', () => { processedPage += 1; loadProcessedEvents(); });
});
