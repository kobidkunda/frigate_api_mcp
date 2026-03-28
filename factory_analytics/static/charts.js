async function chartsApi(url){
  const res = await fetch(url);
  if(!res.ok){ throw new Error(await res.text() || `Request failed: ${res.status}`); }
  return await res.json();
}

async function loadCharts(){
  const [heatmap, heatmapGroup, shift, camera, failures, confidence] = await Promise.all([
    chartsApi('/api/charts/heatmap'),
    chartsApi('/api/charts/heatmap-by-group'),
    chartsApi('/api/charts/shift-summary'),
    chartsApi('/api/charts/camera-summary'),
    chartsApi('/api/charts/job-failures'),
    chartsApi('/api/charts/confidence-distribution'),
  ]);

  const heatmapView = document.getElementById('heatmapView');
  heatmapView.className = "space-y-4 overflow-auto max-h-64 p-2";
  heatmapView.innerHTML = `
    <div class="space-y-2">
      <h4 class="text-[10px] uppercase font-label text-outline tracking-widest">By Camera</h4>
      <table class="w-full text-left text-xs border-collapse">
        <thead class="sticky top-0 bg-surface-container-lowest">
          <tr class="text-outline border-b border-outline-variant/10">
            <th class="py-2">Camera</th><th class="py-2">Hour</th><th class="py-2">Count</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/5">
          ${(heatmap.rows||[]).map(r=>`<tr><td class="py-2">${r.camera_name}</td><td>${r.hour_bucket}:00</td><td>${r.count}</td></tr>`).join('')}
        </tbody>
      </table>
    </div>`;

  const shiftView = document.getElementById('shiftSummaryView');
  shiftView.innerHTML = `
    <div class="flex items-center justify-around h-full">
      <div class="text-center">
        <div class="text-2xl font-headline font-bold text-primary">${(shift.series||{}).day || 0}</div>
        <div class="text-[10px] uppercase font-label text-outline">Day Shift</div>
      </div>
      <div class="w-px h-12 bg-outline-variant/20"></div>
      <div class="text-center">
        <div class="text-2xl font-headline font-bold text-secondary">${(shift.series||{}).night || 0}</div>
        <div class="text-[10px] uppercase font-label text-outline">Night Shift</div>
      </div>
    </div>`;

  const cameraView = document.getElementById('cameraSummaryView');
  cameraView.className = "overflow-auto max-h-64 p-2";
  cameraView.innerHTML = `
    <table class="w-full text-left text-xs border-collapse">
      <thead class="sticky top-0 bg-surface-container-lowest">
        <tr class="text-outline border-b border-outline-variant/10">
          <th class="py-2">Camera</th><th class="py-2">Label</th><th class="py-2">Count</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/5">
        ${(camera.rows||[]).map(r=>`<tr><td class="py-2 font-medium">${r.camera_name}</td><td class="capitalize">${r.label}</td><td>${r.count}</td></tr>`).join('')}
      </tbody>
    </table>`;

  const failuresView = document.getElementById('jobFailuresView');
  failuresView.className = "overflow-auto max-h-64 p-2";
  failuresView.innerHTML = `
    <table class="w-full text-left text-xs border-collapse">
      <thead class="sticky top-0 bg-surface-container-lowest">
        <tr class="text-outline border-b border-outline-variant/10">
          <th class="py-2">Day</th><th class="py-2 text-right">Failures</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/5">
        ${(failures.rows||[]).map(r=>`<tr><td class="py-2">${r.day}</td><td class="text-right text-error font-bold">${r.failures}</td></tr>`).join('')}
      </tbody>
    </table>`;

  const confidenceView = document.getElementById('confidenceDistributionView');
  confidenceView.className = "p-4";
  confidenceView.innerHTML = `
    <div class="flex items-end justify-between gap-2 h-32">
      ${(confidence.rows||[]).map(r => {
        const height = Math.max(5, Math.min(100, (r.count / Math.max(...confidence.rows.map(x=>x.count))) * 100));
        return `
          <div class="flex-1 flex flex-col items-center gap-2">
            <div class="w-full bg-primary/20 rounded-t relative group" style="height: ${height}%">
              <div class="absolute -top-6 left-1/2 -translate-x-1/2 bg-surface-container text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">${r.count}</div>
              <div class="absolute inset-0 bg-primary opacity-40 rounded-t"></div>
            </div>
            <span class="text-[8px] text-outline font-label uppercase truncate w-full text-center">${r.bucket}</span>
          </div>
        `;
      }).join('')}
    </div>`;
}

document.addEventListener('DOMContentLoaded', loadCharts);
