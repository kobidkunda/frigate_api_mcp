# 2026-04-01 - Evidence Photo Auto-Delete Setting

## Summary
Added automatic cleanup of evidence photos older than X days while preserving database records. New setting `evidence_retention_days` (default 30) controls retention period.

## Why
- Evidence photos accumulate and consume disk space
- Historical analytics data should remain in database
- Users need control over retention period
- Factory operations need both historical records and disk space management

## Scope
- New setting `evidence_retention_days` (default 30 days)
- Daily cleanup task in worker loop (runs once per day at midnight UTC)
- Database methods to track and clear expired evidence references
- UI setting in Image Processing section

## Changed files
- `factory_analytics/database.py` - Added `evidence_retention_days` default, `get_expired_evidence_paths()`, `clear_segment_evidence_refs()` methods
- `factory_analytics/worker.py` - Added `_cleanup_old_evidence()` and `_cleanup_empty_dirs()` methods, runs daily
- `factory_analytics/templates/settings.html` - Added Evidence Retention field in Image Processing section

## Decisions
- Cleanup runs once per day (not every loop iteration) to minimize overhead
- Files deleted from filesystem, DB records preserved with evidence_path set to NULL
- Empty evidence subdirectories automatically removed
- Setting 0 disables cleanup entirely
- Default 30 days balances disk usage with recent evidence availability

## Verification
- App restart required to pick up new setting
- Check worker logs for "Cleaned up X evidence files" message

## Risks / Follow-ups
- Consider manual trigger endpoint for immediate cleanup
- Consider separate retention for group vs individual evidence
- May want to add evidence size stats to dashboard

## Resume point
Restart application and verify evidence retention setting appears in Settings UI.
