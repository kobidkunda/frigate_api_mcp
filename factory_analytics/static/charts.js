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

  document.getElementById('heatmapView').innerHTML = `<h4>By Camera</h4><table><thead><tr><th>Camera</th><th>Hour</th><th>Count</th></tr></thead><tbody>${(heatmap.rows||[]).map(r=>`<tr><td>${r.camera_name}</td><td>${r.hour_bucket}</td><td>${r.count}</td></tr>`).join('')}</tbody></table><h4>By Group</h4><table><thead><tr><th>Group</th><th>Hour</th><th>Count</th></tr></thead><tbody>${(heatmapGroup.rows||[]).map(r=>`<tr><td>${r.group_type}: ${r.group_name}</td><td>${r.hour_bucket}</td><td>${r.count}</td></tr>`).join('')}</tbody></table>`;
  document.getElementById('shiftSummaryView').innerHTML = `<div>Day: ${(shift.series||{}).day || 0}</div><div>Night: ${(shift.series||{}).night || 0}</div>`;
  document.getElementById('cameraSummaryView').innerHTML = `<table><thead><tr><th>Camera</th><th>Label</th><th>Count</th></tr></thead><tbody>${(camera.rows||[]).map(r=>`<tr><td>${r.camera_name}</td><td>${r.label}</td><td>${r.count}</td></tr>`).join('')}</tbody></table>`;
  document.getElementById('jobFailuresView').innerHTML = `<table><thead><tr><th>Day</th><th>Failures</th></tr></thead><tbody>${(failures.rows||[]).map(r=>`<tr><td>${r.day}</td><td>${r.failures}</td></tr>`).join('')}</tbody></table>`;
  document.getElementById('confidenceDistributionView').innerHTML = `<table><thead><tr><th>Bucket</th><th>Count</th></tr></thead><tbody>${(confidence.rows||[]).map(r=>`<tr><td>${r.bucket}</td><td>${r.count}</td></tr>`).join('')}</tbody></table>`;
}

document.addEventListener('DOMContentLoaded', loadCharts);
