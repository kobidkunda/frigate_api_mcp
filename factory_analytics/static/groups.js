async function groupsApi(url, options = {}){
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  if(!res.ok){ throw new Error(await res.text() || `Request failed: ${res.status}`); }
  return await res.json();
}

async function loadGroupsPage(){
  const [groups, cameras] = await Promise.all([groupsApi('/api/groups'), groupsApi('/api/cameras')]);
  const options = cameras.map(c => `<option value="${c.id}">${c.name || c.frigate_name}</option>`).join('');
  const root = document.getElementById('groups-management');
  root.innerHTML = `<table><thead><tr><th>ID</th><th>Type</th><th>Name</th><th>Members</th><th>Add Camera</th><th>Actions</th></tr></thead><tbody>${groups.map(g => `
    <tr>
      <td>${g.id}</td>
      <td><input id="group-type-${g.id}" value="${g.group_type}" /></td>
      <td><input id="group-name-${g.id}" value="${g.name}" /></td>
      <td><div id="group-members-${g.id}">Loading…</div></td>
      <td><select id="group-camera-${g.id}">${options}</select><button type="button" onclick="addCameraToGroupFromPage(${g.id})">Add</button></td>
      <td><button type="button" onclick="saveGroup(${g.id})">Save</button><button type="button" class="danger" onclick="deleteGroup(${g.id})">Delete</button></td>
    </tr>
  `).join('')}</tbody></table>`;
  await Promise.all(groups.map(g => loadGroupMembers(g.id)));
}

async function loadGroupMembers(groupId){
  const members = await groupsApi(`/api/groups/${groupId}/cameras`);
  const el = document.getElementById(`group-members-${groupId}`);
  if(!members.length){ el.textContent = 'No cameras'; return; }
  el.innerHTML = members.map(m => `<div>${m.name || m.frigate_name} <button type="button" onclick="removeCameraFromGroup(${groupId}, ${m.id})">Remove</button></div>`).join('');
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
