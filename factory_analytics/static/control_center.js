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
  configEl.innerHTML = (config.config_files || []).map(c => `<div class="card"><strong>${c.label}</strong><div>${c.path}</div><div>${c.exists ? 'present' : 'missing'}</div><pre>${c.preview || ''}</pre></div>`).join('');
  skillEl.innerHTML = (config.skills?.roots || []).map(r => `<div class="card"><strong>${r.root}</strong><div>${r.exists ? 'present' : 'missing'}</div><div>${(r.items || []).join(', ')}</div></div>`).join('');
  installEl.innerHTML = Object.entries(config.platform_instructions || {}).map(([platform, steps]) => `<div class="card"><strong>${platform}</strong><ol>${steps.map(s => `<li>${s}</li>`).join('')}</ol></div>`).join('');
  mcpEl.innerHTML = `<div class="card"><strong>API</strong><pre>${JSON.stringify(api, null, 2)}</pre></div><div class="card"><strong>Frigate</strong><pre>${JSON.stringify(frigate, null, 2)}</pre></div><div class="card"><strong>Ollama</strong><pre>${JSON.stringify(ollama, null, 2)}</pre></div>`;
}
document.addEventListener('DOMContentLoaded', loadControlCenter);
