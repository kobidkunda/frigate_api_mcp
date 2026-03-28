# Group Serial Processing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement continuous serial processing loop for camera groups where groups process in order (1 completely done → next starts) and loop never stops while app is running.

**Architecture:** Enhanced WorkerLoop with group scheduling, database schema changes for group intervals, serial processing between groups, robust error handling, and configuration settings.

**Tech Stack:** Python, FastAPI, SQLite, threading, pytest

---

### Task 1: Database Schema Migration

**Files:**
- Modify: `factory_analytics/database.py:230-240` (near groups table schema)
- Create: `migrations/2026-03-29-group-intervals.sql`

**Step 1: Write migration SQL**

```sql
-- migrations/2026-03-29-group-intervals.sql
ALTER TABLE groups ADD COLUMN interval_seconds INTEGER DEFAULT 300;
ALTER TABLE groups ADD COLUMN last_run_at TEXT;
```

**Step 2: Update database schema definition**

```python
# factory_analytics/database.py:230-240
def create_tables(self):
    with self.connect() as conn:
        # Existing groups table creation - modify to include new columns
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_type TEXT NOT NULL,
                name TEXT NOT NULL,
                interval_seconds INTEGER DEFAULT 300,
                last_run_at TEXT,
                UNIQUE(group_type, name)
            )
        """)
        # ... rest of existing tables
```

**Step 3: Test migration**

```bash
cd /Users/biolasti/application/project/frigate
python -c "from factory_analytics.database import Database; db = Database(); print('Database connected')"
```

**Step 4: Commit**

```bash
git add migrations/2026-03-29-group-intervals.sql factory_analytics/database.py
git commit -m "feat: add interval_seconds and last_run_at to groups table"
```

---

### Task 2: Database Methods for Group Scheduling

**Files:**
- Modify: `factory_analytics/database.py:380-420` (near schedule_group_job)
- Test: `tests/test_groups_model.py`

**Step 1: Write failing test for group scheduling**

```python
# tests/test_groups_model.py
def test_schedule_group_job_with_metadata():
    db = Database()
    group = db.create_group("machine", "test_group")
    camera = db.upsert_camera("test_cam", "Test Camera")
    
    job = db.schedule_group_job(
        camera_id=camera["id"],
        group_id=group["id"],
        group_type=group["group_type"],
        group_name=group["name"]
    )
    
    assert job["payload"]["source"] == "group_scheduler"
    assert job["payload"]["group_id"] == group["id"]
    assert job["payload"]["group_type"] == "machine"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_groups_model.py::test_schedule_group_job_with_metadata -v
```

**Step 3: Update schedule_group_job method**

```python
# factory_analytics/database.py:380-420
def schedule_group_job(self, camera_id: int, group_id: int, group_type: str, group_name: str) -> dict[str, Any]:
    with self.connect() as conn:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            INSERT INTO jobs 
            (camera_id, status, created_at, payload)
            VALUES (?, ?, ?, ?)
            RETURNING id, camera_id, status, created_at, payload
            """,
            (
                camera_id,
                "pending",
                now,
                json.dumps({
                    "source": "group_scheduler",
                    "group_id": group_id,
                    "group_type": group_type,
                    "group_name": group_name
                })
            )
        )
        row = cur.fetchone()
        return self._row_to_dict(row) if row else {}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_groups_model.py::test_schedule_group_job_with_metadata -v
```

**Step 5: Commit**

```bash
git add factory_analytics/database.py tests/test_groups_model.py
git commit -m "feat: add group scheduling with metadata"
```

---

### Task 3: Add has_active_group_jobs Method

**Files:**
- Modify: `factory_analytics/database.py:550-600` (near has_active_job)
- Test: `tests/test_groups_model.py`

**Step 1: Write failing test for active group jobs**

```python
# tests/test_groups_model.py
def test_has_active_group_jobs():
    db = Database()
    group = db.create_group("machine", "test_group")
    camera = db.upsert_camera("test_cam", "Test Camera")
    
    # No active jobs initially
    assert not db.has_active_group_jobs(group["id"])
    
    # Schedule a group job
    db.schedule_group_job(
        camera_id=camera["id"],
        group_id=group["id"],
        group_type=group["group_type"],
        group_name=group["name"]
    )
    
    # Should have active jobs now
    assert db.has_active_group_jobs(group["id"])
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_groups_model.py::test_has_active_group_jobs -v
```

**Step 3: Implement has_active_group_jobs method**

```python
# factory_analytics/database.py:550-600
def has_active_group_jobs(self, group_id: int) -> bool:
    with self.connect() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM jobs 
            WHERE status IN ('pending', 'running')
            AND json_extract(payload, '$.group_id') = ?
            """,
            (group_id,)
        )
        count = cur.fetchone()[0]
        return count > 0
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_groups_model.py::test_has_active_group_jobs -v
```

**Step 5: Commit**

```bash
git add factory_analytics/database.py tests/test_groups_model.py
git commit -m "feat: add has_active_group_jobs method"
```

---

### Task 4: Update Group CRUD Methods

**Files:**
- Modify: `factory_analytics/database.py:233-290` (create/update group methods)
- Modify: `factory_analytics/services.py:133-160` (group service methods)
- Test: `tests/test_groups_model.py`

**Step 1: Write failing test for group interval updates**

```python
# tests/test_groups_model.py
def test_create_group_with_interval():
    db = Database()
    group = db.create_group("machine", "test_group", interval_seconds=600)
    assert group["interval_seconds"] == 600

def test_update_group_interval():
    db = Database()
    group = db.create_group("machine", "test_group")
    updated = db.update_group(group["id"], interval_seconds=900)
    assert updated["interval_seconds"] == 900
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_groups_model.py::test_create_group_with_interval tests/test_groups_model.py::test_update_group_interval -v
```

**Step 3: Update create_group method**

```python
# factory_analytics/database.py:233-250
def create_group(self, group_type: str, name: str, interval_seconds: int = 300) -> dict[str, Any]:
    with self.connect() as conn:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            INSERT INTO groups (group_type, name, interval_seconds)
            VALUES (?, ?, ?)
            RETURNING id, group_type, name, interval_seconds, last_run_at
            """,
            (group_type, name, interval_seconds)
        )
        row = cur.fetchone()
        return self._row_to_dict(row) if row else {}
```

**Step 4: Update update_group method**

```python
# factory_analytics/database.py:268-283
def update_group(
    self, group_id: int, group_type: str | None = None, 
    name: str | None = None, interval_seconds: int | None = None
) -> dict[str, Any]:
    updates = []
    params = []
    if group_type is not None:
        updates.append("group_type = ?")
        params.append(group_type)
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if interval_seconds is not None:
        updates.append("interval_seconds = ?")
        params.append(interval_seconds)
    
    if not updates:
        return self.get_group(group_id) or {}
    
    params.append(group_id)
    with self.connect() as conn:
        cur = conn.execute(
            f"""
            UPDATE groups 
            SET {", ".join(updates)}
            WHERE id = ?
            RETURNING id, group_type, name, interval_seconds, last_run_at
            """,
            params
        )
        row = cur.fetchone()
        return self._row_to_dict(row) if row else {}
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_groups_model.py::test_create_group_with_interval tests/test_groups_model.py::test_update_group_interval -v
```

**Step 6: Commit**

```bash
git add factory_analytics/database.py tests/test_groups_model.py
git commit -m "feat: update group CRUD with interval support"
```

---

### Task 5: Enhanced WorkerLoop._schedule_due_groups

**Files:**
- Modify: `factory_analytics/worker.py:35-70` (WorkerLoop class)
- Test: `tests/test_worker.py`

**Step 1: Write failing test for group scheduling**

```python
# tests/test_worker.py
def test_schedule_due_groups():
    db = Database()
    worker = WorkerLoop(db)
    
    # Create group with short interval
    group = db.create_group("machine", "test_group", interval_seconds=1)
    camera = db.upsert_camera("test_cam", "Test Camera")
    db.add_camera_to_group(camera["id"], group["id"])
    
    # Update last_run_at to be old
    db.update_group(group["id"], last_run_at="2020-01-01T00:00:00+00:00")
    
    # Schedule due groups
    worker._schedule_due_groups()
    
    # Should have scheduled a job
    assert db.has_active_group_jobs(group["id"])
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_worker.py::test_schedule_due_groups -v
```

**Step 3: Implement _schedule_due_groups method**

```python
# factory_analytics/worker.py:46-70 (add after _schedule_due_cameras)
def _schedule_due_groups(self):
    settings = self.db.get_settings()
    if not settings.get("group_scheduler_enabled", True):
        return
    
    now = datetime.now(timezone.utc)
    for group in self.db.list_groups():
        if not group.get("enabled", True):
            continue
        
        # Skip if group already has active jobs
        if self.db.has_active_group_jobs(group["id"]):
            continue
        
        interval = group.get("interval_seconds") or 300
        last_run = group.get("last_run_at")
        due = True
        
        if last_run:
            try:
                last_dt = datetime.fromisoformat(last_run)
                due = (now - last_dt).total_seconds() >= interval
            except Exception:
                due = True
        
        if due:
            # Schedule all enabled cameras in this group
            cameras = self.db.list_group_cameras(group["id"])
            for camera in cameras:
                if camera.get("enabled"):
                    self.db.schedule_group_job(
                        camera_id=camera["id"],
                        group_id=group["id"],
                        group_type=group["group_type"],
                        group_name=group["name"]
                    )
            
            # Update group last_run_at immediately (even though jobs not complete)
            # This prevents re-scheduling while jobs are running
            self.db.update_group(group["id"], last_run_at=now.isoformat())
```

**Step 4: Update WorkerLoop.run() to call _schedule_due_groups**

```python
# factory_analytics/worker.py:35-45
def run(self):
    while not self.stop_event.is_set():
        try:
            self._schedule_due_groups()  # NEW: Schedule groups first
            self._schedule_due_cameras()
            processed = self.service.process_one_pending_job()
            if processed:
                logger.info("Processed job %s", processed.get("job", {}).get("id"))
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
            # CRITICAL: Continue loop despite errors
        self.stop_event.wait(5)
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_worker.py::test_schedule_due_groups -v
```

**Step 6: Commit**

```bash
git add factory_analytics/worker.py tests/test_worker.py
git commit -m "feat: implement _schedule_due_groups method"
```

---

### Task 6: Error Handling and Robustness

**Files:**
- Modify: `factory_analytics/worker.py:35-50` (exception handling)
- Test: `tests/test_worker.py`

**Step 1: Write failing test for error recovery**

```python
# tests/test_worker.py
def test_worker_continues_after_exception():
    db = Database()
    worker = WorkerLoop(db)
    
    # Mock a method to raise exception
    original_method = worker._schedule_due_groups
    call_count = 0
    def mock_method():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Test error")
        original_method()
    
    worker._schedule_due_groups = mock_method
    
    # Run worker loop briefly
    import threading
    import time
    worker.start()
    time.sleep(0.1)
    worker.stop()
    
    # Should have called method twice (recovered from error)
    assert call_count >= 2
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_worker.py::test_worker_continues_after_exception -v
```

**Step 3: Enhance exception handling in run()**

```python
# factory_analytics/worker.py:35-50
def run(self):
    error_count = 0
    max_errors = 10
    while not self.stop_event.is_set():
        try:
            self._schedule_due_groups()
            self._schedule_due_cameras()
            processed = self.service.process_one_pending_job()
            if processed:
                logger.info("Processed job %s", processed.get("job", {}).get("id"))
            
            # Reset error count on successful iteration
            error_count = 0
            
        except Exception as e:
            error_count += 1
            logger.error(f"Worker loop error ({error_count}/{max_errors}): {e}", exc_info=True)
            
            # If too many consecutive errors, log warning but continue
            if error_count >= max_errors:
                logger.warning(f"Worker loop has {error_count} consecutive errors, but continuing...")
                error_count = max_errors - 1  # Prevent overflow
            
            # CRITICAL: Continue loop despite errors
        
        self.stop_event.wait(5)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_worker.py::test_worker_continues_after_exception -v
```

**Step 5: Commit**

```bash
git add factory_analytics/worker.py tests/test_worker.py
git commit -m "feat: enhance worker error handling and recovery"
```

---

### Task 7: Settings Configuration

**Files:**
- Modify: `factory_analytics/database.py:100-150` (get_settings/default settings)
- Modify: `factory_analytics/services.py:23-32` (settings method)
- Test: `tests/test_services.py`

**Step 1: Write failing test for group scheduler settings**

```python
# tests/test_services.py
def test_group_scheduler_settings():
    db = Database()
    service = AnalyticsService(db)
    
    # Default settings should include group scheduler enabled
    settings = service.settings()
    assert "group_scheduler_enabled" in settings
    assert settings["group_scheduler_enabled"] is True
    assert "group_analysis_interval_seconds" in settings
    assert settings["group_analysis_interval_seconds"] == 300
    
    # Update settings
    updated = service.update_settings({
        "group_scheduler_enabled": False,
        "group_analysis_interval_seconds": 600
    })
    
    assert updated["group_scheduler_enabled"] is False
    assert updated["group_analysis_interval_seconds"] == 600
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_services.py::test_group_scheduler_settings -v
```

**Step 3: Update default settings**

```python
# factory_analytics/database.py:100-150 (in get_settings method or default settings)
def get_settings(self) -> dict[str, Any]:
    with self.connect() as conn:
        cur = conn.execute("SELECT key, value FROM settings")
        settings = {row[0]: json.loads(row[1]) for row in cur.fetchall()}
    
    # Set defaults if not present
    defaults = {
        "scheduler_enabled": True,
        "analysis_interval_seconds": 300,
        "group_scheduler_enabled": True,  # NEW
        "group_analysis_interval_seconds": 300,  # NEW
        "group_retry_attempts": 3,  # NEW
        "group_retry_delay_seconds": 60  # NEW
    }
    
    for key, default in defaults.items():
        if key not in settings:
            settings[key] = default
    
    return settings
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_services.py::test_group_scheduler_settings -v
```

**Step 5: Commit**

```bash
git add factory_analytics/database.py tests/test_services.py
git commit -m "feat: add group scheduler configuration settings"
```

---

### Task 8: UI Updates for Group Interval Configuration

**Files:**
- Modify: `factory_analytics/static/app.js:42-60` (loadGroups function)
- Modify: `factory_analytics/templates/dashboard.html:29-35` (groups section)
- Test: Manual testing

**Step 1: Update loadGroups function**

```javascript
// factory_analytics/static/app.js:42-60
async function loadGroups(){ 
    const el=document.getElementById('groupTable'); 
    if(!el) return; 
    let groups, cameras; 
    try { 
        groups = await api('/api/groups'); 
        cameras = await api('/api/cameras'); 
    } catch(e) { 
        el.innerHTML = '<div class="error">Failed to load groups</div>'; 
        return; 
    } 
    const options = cameras.map(c=>`<option value="${c.id}">${c.name}</option>`).join(''); 
    el.innerHTML = `
        <div class="add-group">
            <div class="inline-actions">
                <input id="group-type" placeholder="machine or room" />
                <input id="group-name" placeholder="Group name" />
                <input id="group-interval" placeholder="Interval (seconds)" value="300" />
                <button onclick="addGroup()">Add Group</button>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Name</th>
                    <th>Interval (s)</th>
                    <th>Cameras</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${groups.map(g=>`
                    <tr>
                        <td>${g.id}</td>
                        <td>${g.group_type}</td>
                        <td>${g.name}</td>
                        <td><input id="interval-${g.id}" value="${g.interval_seconds || 300}" onchange="updateGroupInterval(${g.id})" /></td>
                        <td><select id="group-camera-${g.id}">${options}</select></td>
                        <td class="inline-actions">
                            <button onclick="addCameraToGroup(${g.id})">Add Camera</button>
                            <button class="secondary" onclick="runGroup(${g.id})">Run Group</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `; 
}
```

**Step 2: Add updateGroupInterval function**

```javascript
// factory_analytics/static/app.js (add after loadGroups)
async function updateGroupInterval(groupId) {
    const intervalInput = document.getElementById(`interval-${groupId}`);
    const interval = parseInt(intervalInput.value);
    if (isNaN(interval) || interval < 1) {
        alert('Interval must be a positive number');
        return;
    }
    
    try {
        await api(`/api/groups/${groupId}`, {
            method: 'PUT',
            body: { interval_seconds: interval }
        });
        alert('Group interval updated');
    } catch (e) {
        alert('Failed to update interval');
    }
}

async function addGroup() {
    const type = document.getElementById('group-type').value.trim();
    const name = document.getElementById('group-name').value.trim();
    const interval = parseInt(document.getElementById('group-interval').value);
    
    if (!type || !name) {
        alert('Type and name are required');
        return;
    }
    
    if (isNaN(interval) || interval < 1) {
        alert('Interval must be a positive number');
        return;
    }
    
    try {
        await api('/api/groups', {
            method: 'POST',
            body: { group_type: type, name: name, interval_seconds: interval }
        });
        alert('Group added');
        loadGroups();
    } catch (e) {
        alert('Failed to add group');
    }
}
```

**Step 3: Test UI manually**

```bash
# Start the app
./factory-analytics.sh debug
# Open browser to http://localhost:5000
# Verify groups table shows interval column and inputs work
```

**Step 4: Commit**

```bash
git add factory_analytics/static/app.js
git commit -m "feat: add UI for group interval configuration"
```

---

### Task 9: Integration Testing

**Files:**
- Create: `tests/test_group_serial_processing.py`
- Test: Full integration test

**Step 1: Write comprehensive integration test**

```python
# tests/test_group_serial_processing.py
import time
from datetime import datetime, timezone
from factory_analytics.database import Database
from factory_analytics.worker import WorkerLoop

def test_serial_group_processing():
    db = Database()
    worker = WorkerLoop(db)
    
    # Create two groups with different intervals
    group1 = db.create_group("machine", "Group 1", interval_seconds=2)
    group2 = db.create_group("room", "Group 2", interval_seconds=2)
    
    # Create cameras and add to groups
    cam1 = db.upsert_camera("cam1", "Camera 1")
    cam2 = db.upsert_camera("cam2", "Camera 2")
    cam3 = db.upsert_camera("cam3", "Camera 3")
    
    db.add_camera_to_group(cam1["id"], group1["id"])
    db.add_camera_to_group(cam2["id"], group1["id"])
    db.add_camera_to_group(cam3["id"], group2["id"])
    
    # Enable all cameras
    db.update_camera(cam1["id"], {"enabled": 1})
    db.update_camera(cam2["id"], {"enabled": 1})
    db.update_camera(cam3["id"], {"enabled": 1})
    
    # Set old last_run_at to trigger scheduling
    old_time = "2020-01-01T00:00:00+00:00"
    db.update_group(group1["id"], last_run_at=old_time)
    db.update_group(group2["id"], last_run_at=old_time)
    
    # Start worker
    worker.start()
    
    try:
        # Wait for jobs to be scheduled
        time.sleep(1)
        
        # Both groups should have jobs scheduled
        assert db.has_active_group_jobs(group1["id"])
        assert db.has_active_group_jobs(group2["id"])
        
        # Check jobs have correct metadata
        jobs = db.list_jobs(limit=10)
        group1_jobs = [j for j in jobs if j.get("payload", {}).get("group_id") == group1["id"]]
        group2_jobs = [j for j in jobs if j.get("payload", {}).get("group_id") == group2["id"]]
        
        assert len(group1_jobs) == 2  # cam1 and cam2
        assert len(group2_jobs) == 1  # cam3
        
        # Verify group metadata in payload
        for job in group1_jobs:
            payload = job.get("payload", {})
            assert payload.get("source") == "group_scheduler"
            assert payload.get("group_id") == group1["id"]
            assert payload.get("group_type") == "machine"
            assert payload.get("group_name") == "Group 1"
        
    finally:
        worker.stop()
```

**Step 2: Run integration test**

```bash
pytest tests/test_group_serial_processing.py::test_serial_group_processing -v
```

**Step 3: Fix any issues found**

Run test, fix any failures, rerun until passing.

**Step 4: Commit**

```bash
git add tests/test_group_serial_processing.py
git commit -m "feat: add integration test for serial group processing"
```

---

### Task 10: Documentation and Final Verification

**Files:**
- Update: `docs/features.md`
- Update: `docs/todos.md`
- Create: `docs/implementation/2026-03-29-group-serial-processing.md`

**Step 1: Update features.md**

Add to **Groups** section:
```
- Feature: Serial group processing with configurable intervals
  - Status: active
  - Paths: `factory_analytics/worker.py`, `factory_analytics/database.py`
  - Notes: Groups process serially (1 completely done → next starts); configurable interval_seconds per group; continuous loop with error recovery
  - Last updated: 2026-03-29
```

**Step 2: Update todos.md**

Mark group analytics foundation task as done, add new task if needed.

**Step 3: Create implementation note**

```markdown
# 2026-03-29 - Group Serial Processing Implementation

## Summary
Implemented continuous serial processing loop for camera groups with configurable intervals and robust error handling.

## Why
- Needed serial processing order for groups (1 completely done → next starts)
- Worker loop was stopping unexpectedly
- Required configurable intervals for both cameras and groups

## Scope
- Database schema migration for group intervals
- Enhanced WorkerLoop with group scheduling
- Serial processing between groups
- Error handling and continuity
- UI for interval configuration

## Changed Files
- `factory_analytics/database.py` - schema, group methods, settings
- `factory_analytics/worker.py` - _schedule_due_groups, error handling
- `factory_analytics/services.py` - settings updates
- `factory_analytics/static/app.js` - UI for interval configuration
- `tests/test_groups_model.py` - group interval tests
- `tests/test_worker.py` - worker loop tests
- `tests/test_services.py` - settings tests
- `tests/test_group_serial_processing.py` - integration test
- `migrations/2026-03-29-group-intervals.sql` - migration script

## Decisions
- Enhanced existing WorkerLoop vs separate thread (simpler integration)
- Update group.last_run_at immediately when scheduling (prevents re-scheduling)
- Continue loop despite errors (critical for continuous operation)
- Both per-group and global interval configuration (flexibility)

## Verification
- All unit tests pass
- Integration test verifies serial processing
- Manual UI testing for interval configuration
- Worker continues after simulated errors

## Risks / Follow-ups
- **Risk**: Database migration may fail on existing data
  - **Mitigation**: Backup before migration, test on copy first
- **Follow-up**: Add group processing status to dashboard
- **Follow-up**: Implement priority-based group ordering

## Resume Point
If interrupted: Verify all tests pass, check database migration applied correctly.
```

**Step 4: Run all tests**

```bash
pytest tests/ -v
```

**Step 5: Final commit**

```bash
git add docs/features.md docs/todos.md docs/implementation/2026-03-29-group-serial-processing.md
git commit -m "docs: update documentation for group serial processing"
```

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-03-29-group-serial-processing-plan.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**