# 2026-03-29 - Group Serial Processing Design

## Summary
Implement continuous serial processing loop for camera groups where groups process in order (1 completely done → next starts) and loop never stops while app is running.

## Why
- Current system processes cameras individually without group coordination
- Worker loop stops unexpectedly breaking continuous processing
- No serial processing order for groups
- Need configurable intervals per camera AND per group

## Scope
### Included
- Database schema changes for group intervals
- Enhanced worker loop with group scheduling
- Serial processing between groups
- Robust error handling and continuity
- Configuration settings for group scheduling
- Integration with existing group analysis features

### Not Included  
- Real-time video processing changes
- Frigate integration modifications  
- Ollama analysis algorithm changes
- UI redesign beyond configuration additions

## Architecture

### Database Schema Changes
```sql
-- Add interval_seconds to groups table
ALTER TABLE groups ADD COLUMN interval_seconds INTEGER DEFAULT 300;

-- Add last_run_at to track when group was last analyzed  
ALTER TABLE groups ADD COLUMN last_run_at TEXT;
```

### Enhanced Worker Loop
**Current WorkerLoop.run():**
```python
while not self.stop_event.is_set():
    try:
        self._schedule_due_cameras()
        processed = self.service.process_one_pending_job()
    except Exception:
        logger.exception("Worker loop error")
    self.stop_event.wait(5)
```

**Enhanced WorkerLoop.run():**
```python
while not self.stop_event.is_set():
    try:
        # New: Schedule due groups (serial processing)
        self._schedule_due_groups()
        
        # Existing: Schedule individual cameras
        self._schedule_due_cameras()
        
        # Process one pending job
        processed = self.service.process_one_pending_job()
    except Exception as e:
        logger.error(f"Worker loop error: {e}", exc_info=True)
        # Critical: Continue loop despite errors
    self.stop_event.wait(5)
```

### Serial Processing Flow
```
Continuous Loop:
  1. Check for due groups (enabled, interval passed, no active jobs)
  2. For each due group (processed serially):
     a. Schedule all enabled cameras in group with group metadata
     b. Monitor job completion for this group
     c. Only when ALL group jobs complete → update group.last_run_at
     d. Move to next group (Group 2 doesn't start until Group 1 complete)
  
  3. Check for due individual cameras (non-group, existing logic)
  4. Process any pending jobs (existing logic)
  
  5. Sleep briefly, repeat forever
```

### Error Handling & Continuity
1. **Comprehensive Exception Wrapping**: No uncaught exceptions stop loop
2. **Health Monitoring**: Watchdog timer detects stalled loops
3. **Retry Logic**: Configurable retries for failed groups
4. **State Persistence**: Survive app restarts without losing context
5. **Graceful Degradation**: Skip problematic groups temporarily

### Configuration Settings
**New Settings:**
- `group_scheduler_enabled` (bool): Enable/disable group scheduling
- `group_analysis_interval_seconds` (int): Default group interval (300)
- `group_retry_attempts` (int): Max retries for failed groups (3)
- `group_retry_delay_seconds` (int): Delay between retries (60)

**Per-Group Configuration:**
- `interval_seconds`: Override default interval
- `enabled`: Enable/disable group scheduling
- `last_run_at`: Track last analysis time

## Integration Points

### With Existing Features
- **Camera Scheduling**: Maintains existing individual camera scheduling
- **Group Analysis**: Uses existing `merge_group_snapshots()` and `queue_group_analysis()`
- **Job Processing**: Works with current `process_one_pending_job()`
- **Database**: Extends groups table, maintains audit logs
- **UI**: Add interval configuration to Groups page

### API Compatibility
- All existing endpoints remain unchanged
- New optional fields in group creation/update
- Backward compatible migration

## Risks / Follow-ups

### Risks
1. **Database Migration**: Schema changes require careful rollout
2. **Performance Impact**: Monitoring group completion adds overhead
3. **Error Handling Complexity**: Robust continuity requires careful implementation

### Mitigations
1. **Incremental Rollout**: Test with small subset first
2. **Performance Monitoring**: Add metrics for group processing times
3. **Comprehensive Testing**: Unit tests for all error scenarios

### Follow-ups
1. **UI Enhancements**: Real-time group processing status display
2. **Advanced Scheduling**: Priority-based group ordering
3. **Analytics**: Group processing performance metrics

## Verification Plan
1. **Unit Tests**: Worker loop with group scheduling
2. **Integration Tests**: Full serial processing flow
3. **Error Scenario Tests**: Worker recovery from failures
4. **Performance Tests**: Continuous operation under load
5. **Migration Tests**: Database schema upgrade/downgrade

## Changed Files
- `factory_analytics/database.py`: Schema changes, new queries
- `factory_analytics/worker.py`: Enhanced WorkerLoop with group scheduling
- `factory_analytics/services.py`: Group interval configuration
- `factory_analytics/static/app.js`: UI for group interval settings
- `factory_analytics/templates/groups.html`: Interval configuration fields
- Migration script for schema changes

## Decisions
- **Approach Choice**: Enhanced existing worker vs separate thread (chose enhanced for simplicity)
- **Serial vs Parallel**: Groups serial, cameras within group parallel (maintains existing behavior)
- **Error Handling**: Continue loop at all costs vs stopping on critical errors (chose continue)
- **Configuration**: Per-group intervals vs global only (chose both configurable)

## Resume Point
If interrupted during implementation:
1. Check database schema migration status
2. Verify WorkerLoop._schedule_due_groups() implementation
3. Test serial processing with mock groups
4. Add error handling and recovery logic
5. Update UI for interval configuration