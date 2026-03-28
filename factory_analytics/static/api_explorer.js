async function loadApiExplorer() {
  const catalogEl = document.getElementById('api-catalog');
  const notesEl = document.getElementById('skill-usage-notes');
  if (!catalogEl || !notesEl) return;
  const response = await fetch('/api/api-explorer/catalog');
  const payload = await response.json();
  catalogEl.innerHTML = (payload.groups || []).map(group => `
    <div class="bg-surface-container p-4 rounded-lg space-y-4">
      <h3 class="font-headline font-bold text-primary uppercase text-xs tracking-widest border-b border-outline-variant/10 pb-2">${group.name}</h3>
      <div class="space-y-3">
        ${group.routes.map(route => `
          <div class="bg-surface-container-lowest p-3 rounded border border-outline-variant/5 hover:border-primary/20 transition-colors">
            <div class="flex items-center gap-3 mb-1">
              <span class="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-bold rounded uppercase">${route.methods.join(', ')}</span>
              <code class="text-xs font-mono text-on-surface">${route.path}</code>
            </div>
            <div class="text-sm font-semibold text-on-surface-variant">${route.name}</div>
            <div class="text-[10px] text-outline italic mt-1">${route.skill_notes}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
  notesEl.innerHTML = '<p>Use safe GET endpoints directly for monitoring. Use skill-aware workflows for settings, groups, jobs, and history interactions.</p>';
}
document.addEventListener('DOMContentLoaded', loadApiExplorer);
