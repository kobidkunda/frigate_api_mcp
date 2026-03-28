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
- `factory_analytics/main.py` - Added interval support to group endpoints
- `tests/test_groups_model.py` - group interval tests
- `tests/test_worker.py` - worker loop tests
- `tests/test_services.py` - settings tests
- `tests/test_group_serial_processing.py` - integration test
- `factory_analytics/migrations/2026-03-29-group-intervals.sql` - migration script

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
Finished implementation.
