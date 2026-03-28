async function loadApiExplorer() {
  const catalogEl = document.getElementById('api-catalog');
  const notesEl = document.getElementById('skill-usage-notes');
  if (!catalogEl || !notesEl) return;
  const response = await fetch('/api/api-explorer/catalog');
  const payload = await response.json();
  catalogEl.innerHTML = (payload.groups || []).map(group => `<section class="card"><h3>${group.name}</h3>${group.routes.map(route => `<div><strong>${route.methods.join(', ')}</strong> <code>${route.path}</code><div>${route.name}</div><div>${route.skill_notes}</div></div>`).join('')}</section>`).join('');
  notesEl.innerHTML = '<p>Use safe GET endpoints directly for monitoring. Use skill-aware workflows for settings, groups, jobs, and history interactions.</p>';
}
document.addEventListener('DOMContentLoaded', loadApiExplorer);
