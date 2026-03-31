# 2026-03-31 - Worker Scheduler Indentation Fix

## Summary
Fixed a critical Python indentation bug in the worker scheduler that caused `UnboundLocalError` for the `due` variable, preventing group analysis jobs from being scheduled.

## Why
- The worker was continuously crashing with `UnboundLocalError: cannot access local variable 'due' where it is not associated with a value`
- Group analysis was not running because the scheduler couldn't check if groups were due for analysis
- The error was masked by the worker's error recovery mechanism (10 consecutive errors before warning)

## Root Cause
In `factory_analytics/worker.py`, the `_schedule_due_groups` method had incorrect indentation:
- Line 89 `if due:` had 8-space indentation (same level as the `for group in self.db.list_groups():` loop)
- This meant `if due:` was OUTSIDE the for loop, not inside it
- When the for loop completed, `due` was out of scope, causing the UnboundLocalError

The issue was hidden by:
1. Python cache (`__pycache__`) not being cleared
2. The error handling in the worker loop which logs but continues

## Scope
- Fixed indentation in `_schedule_due_groups` method
- Fixed similar issue in `_schedule_due_cameras` method (proactive fix)
- Added `job_type` parameter to `Database.list_jobs_paginated()` to support filtering

## Changed files
- `factory_analytics/worker.py` - Rewrote with correct indentation for both scheduler methods
- `factory_analytics/database.py` - Added `job_type` parameter to `list_jobs_paginated()`

## Verification
```bash
# Test the worker method directly
.venv/bin/python3 -c "
from factory_analytics.worker import WorkerLoop
from factory_analytics.database import Database
db = Database()
worker = WorkerLoop(db)
worker._schedule_due_groups()
print('SUCCESS')
"

# Check logs for successful job processing
tail -50 logs/api.log | grep "Processed job"

# Verify group analysis is merging all cameras
curl -s "http://192.168.88.81:8090/api/jobs?limit=5&job_type=group_analysis" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for j in d['jobs'][:5]:
    raw = j.get('raw_result')
    if isinstance(raw, str):
        import json as j2
        raw = j2.loads(raw)
    inc = raw.get('included_cameras', []) if isinstance(raw, dict) else []
    print(f'Job {j[\"id\"]}: {j[\"status\"]} - included: {inc}')
"
# Output shows: included: ['camera_88_2', 'camera_88_4'] for successful jobs
```

## Decisions
- Rewrote the entire worker.py file to ensure consistent indentation (spaces, not tabs)
- Added job_type filter to the jobs API endpoint to support filtering by job type

## Risks / Follow-ups
- None identified - the fix is straightforward

## Resume point
Task complete. Group analysis is now working correctly with all cameras being merged into a single composite image.
