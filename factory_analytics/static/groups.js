async function groupsApi(url, options = {}){
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  if(!res.ok){ throw new Error(await res.text() || `Request failed: ${res.status}`); }
  return await res.json();
}

async function loadGroupsPage(){
  const [groups, cameras] = await Promise.all([groupsApi('/api/groups'), groupsApi('/api/cameras')]);
  const options = cameras.map(c => `<option value="${c.id}">${c.name || c.frigate_name}</option>`).join('');
  const root = document.getElementById('groups-management');
  root.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-surface-container text-outline text-[10px] uppercase tracking-[0.2em] font-label border-b border-outline-variant/10">
            <th class="px-4 py-3 font-semibold">ID</th>
            <th class="px-4 py-3 font-semibold">Type</th>
            <th class="px-4 py-3 font-semibold">Name</th>
            <th class="px-4 py-3 font-semibold">Members</th>
            <th class="px-4 py-3 font-semibold">Add Member</th>
            <th class="px-4 py-3 font-semibold text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/5">
          ${groups.map(g => `
            <tr class="hover:bg-surface-container-highest/20 transition-colors">
              <td class="px-4 py-4 text-xs font-label text-primary">#GRP-${g.id}</td>
              <td class="px-4 py-4">
                <input id="group-type-${g.id}" value="${g.group_type}" class="bg-surface-container-lowest border-none text-xs p-2 rounded focus:ring-1 focus:ring-primary w-24" />
              </td>
              <td class="px-4 py-4">
                <input id="group-name-${g.id}" value="${g.name}" class="bg-surface-container-lowest border-none text-xs p-2 rounded focus:ring-1 focus:ring-primary w-full" />
              </td>
              <td class="px-4 py-4">
                <div id="group-members-${g.id}" class="flex flex-wrap gap-1 max-w-xs">
                  <span class="text-[10px] text-outline italic">Loading…</span>
                </div>
              </td>
              <td class="px-4 py-4">
                <div class="flex gap-1">
                  <select id="group-camera-${g.id}" class="bg-surface-container-lowest border-none text-[10px] p-1.5 rounded focus:ring-0 flex-1">${options}</select>
                  <button type="button" onclick="addCameraToGroupFromPage(${g.id})" class="bg-primary-container text-primary text-[10px] font-bold uppercase px-2 py-1 hover:bg-on-primary-fixed-variant transition-all rounded">Add</button>
                </div>
              </td>
              <td class="px-4 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <button type="button" onclick="saveGroup(${g.id})" class="text-primary hover:bg-primary/10 p-1.5 rounded transition-colors" title="Save Changes">
                    <span class="material-symbols-outlined text-sm">save</span>
                  </button>
                  <button type="button" onclick="deleteGroup(${g.id})" class="text-error/60 hover:bg-error/10 p-1.5 rounded transition-colors" title="Delete Group">
                    <span class="material-symbols-outlined text-sm">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
  await Promise.all(groups.map(g => loadGroupMembers(g.id)));
}

async function loadGroupMembers(groupId){
  const members = await groupsApi(`/api/groups/${groupId}/cameras`);
  const el = document.getElementById(`group-members-${groupId}`);
  if(!members.length){ el.innerHTML = '<span class="text-[10px] text-outline italic">Empty Group</span>'; return; }
  el.innerHTML = members.map(m => `
    <div class="flex items-center gap-1 bg-surface-container-highest px-2 py-0.5 rounded-full border border-outline-variant/10">
      <span class="text-[10px] font-medium text-on-surface-variant truncate max-w-[80px]">${m.name || m.frigate_name}</span>
      <button type="button" onclick="removeCameraFromGroup(${groupId}, ${m.id})" class="text-outline hover:text-error transition-colors">
        <span class="material-symbols-outlined text-[12px]">close</span>
      </button>
    </div>`).join('');
}

async function createGroupFromPage(){
  const group_type = document.getElementById('groups-new-type').value.trim();
  const name = document.getElementById('groups-new-name').value.trim();
  if(!group_type || !name){ alert('Enter group type and name'); return; }
  await groupsApi('/api/groups', { method: 'POST', body: JSON.stringify({ group_type, name }) });
  await loadGroupsPage();
}

async function saveGroup(groupId){
  const group_type = document.getElementById(`group-type-${groupId}`).value.trim();
  const name = document.getElementById(`group-name-${groupId}`).value.trim();
  await groupsApi(`/api/groups/${groupId}`, { method: 'PUT', body: JSON.stringify({ group_type, name }) });
  await loadGroupsPage();
}

async function deleteGroup(groupId){
  if(!confirm('Delete this group?')) return;
  await groupsApi(`/api/groups/${groupId}`, { method: 'DELETE' });
  await loadGroupsPage();
}

async function addCameraToGroupFromPage(groupId){
  const camera_id = Number(document.getElementById(`group-camera-${groupId}`).value);
  await groupsApi(`/api/groups/${groupId}/cameras`, { method: 'POST', body: JSON.stringify({ camera_id }) });
  await loadGroupMembers(groupId);
}

async function removeCameraFromGroup(groupId, cameraId){
  await groupsApi(`/api/groups/${groupId}/cameras/${cameraId}`, { method: 'DELETE' });
  await loadGroupMembers(groupId);
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('groups-create-btn').addEventListener('click', createGroupFromPage);
  loadGroupsPage();
});
