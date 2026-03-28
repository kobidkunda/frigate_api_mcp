async function loadControlCenter() {
  const configEl = document.getElementById('config-files');
  const mcpEl = document.getElementById('mcp-status');
  const skillEl = document.getElementById('skill-files');
  const installEl = document.getElementById('platform-instructions');
  if (!configEl || !mcpEl || !skillEl || !installEl) return;
  const [configRes, apiRes, frigateRes, ollamaRes] = await Promise.all([
    fetch('/api/control-center/config'),
    fetch('/api/health'),
    fetch('/api/health/frigate'),
    fetch('/api/health/ollama'),
  ]);
  const config = await configRes.json();
  const api = await apiRes.json();
  const frigate = await frigateRes.json();
  const ollama = await ollamaRes.json();
  
  configEl.innerHTML = (config.config_files || []).map(c => `
    <div class="bg-surface-container p-4 rounded-lg space-y-2">
      <div class="flex justify-between items-center">
        <strong class="text-sm font-headline text-on-surface">${c.label}</strong>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${c.exists ? 'bg-tertiary/10 text-tertiary' : 'bg-error/10 text-error'}">${c.exists ? 'present' : 'missing'}</span>
      </div>
      <code class="block text-[10px] text-outline font-mono truncate">${c.path}</code>
      <pre class="bg-surface-container-lowest p-3 rounded text-[10px] font-mono text-on-surface-variant border border-outline-variant/5 overflow-auto max-h-32">${c.preview || 'No preview available'}</pre>
    </div>
  `).join('');

  skillEl.innerHTML = (config.skills?.roots || []).map(r => `
    <div class="bg-surface-container p-4 rounded-lg space-y-2">
      <div class="flex justify-between items-center">
        <strong class="text-sm font-headline text-on-surface">${r.root}</strong>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${r.exists ? 'bg-tertiary/10 text-tertiary' : 'bg-error/10 text-error'}">${r.exists ? 'present' : 'missing'}</span>
      </div>
      <div class="flex flex-wrap gap-1">
        ${(r.items || []).map(item => `<span class="px-2 py-0.5 bg-surface-container-highest text-[10px] rounded text-outline">${item}</span>`).join('')}
      </div>
    </div>
  `).join('');

  installEl.innerHTML = Object.entries(config.platform_instructions || {}).map(([platform, steps]) => `
    <div class="bg-surface-container p-4 rounded-lg space-y-3">
      <strong class="text-sm font-headline text-primary uppercase tracking-widest">${platform}</strong>
      <ol class="space-y-2 list-decimal list-inside text-xs text-on-surface-variant">
        ${steps.map(s => `<li>${s}</li>`).join('')}
      </ol>
    </div>
  `).join('');

  const statusCards = [
    { name: 'API', data: api, color: 'text-primary' },
    { name: 'Frigate', data: frigate, color: 'text-secondary' },
    { name: 'Ollama', data: ollama, color: 'text-tertiary' }
  ];

  mcpEl.innerHTML = statusCards.map(s => `
    <div class="bg-surface-container p-4 rounded-lg space-y-2">
      <strong class="text-sm font-headline ${s.color} uppercase tracking-widest">${s.name}</strong>
      <pre class="bg-surface-container-lowest p-3 rounded text-[10px] font-mono text-on-surface-variant border border-outline-variant/5 overflow-auto max-h-48">${JSON.stringify(s.data, null, 2)}</pre>
    </div>
  `).join('');
}
document.addEventListener('DOMContentLoaded', loadControlCenter);
