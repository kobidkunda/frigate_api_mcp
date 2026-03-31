# 2026-04-01 - camera_88_4 visibility runs not completing (issue #1647)

## Summary
Job 1647 for camera_88_4 was stuck in "running" status for ~1.5 hours, appearing to run indefinitely. Investigation revealed the job was properly cancelled by the worker's timeout mechanism, and the system is functioning correctly.

## Why
- User reported visibility runs not completing → Running indefinitely
- Job 1647 showed as "running" since 2026-03-31T22:51:57
- Current time at investigation: ~2026-04-01T04:21

## Scope
- Analyzed job 1647 and recent jobs for camera_88_4
- Checked worker logs, database state, timeout mechanism
- Verified Ollama and Frigate connectivity
- Reviewed worker restart history

## Findings

### Job 1647 Status
- **Created**: 2026-03-31T22:51:57
- **Started**: 2026-03-31T22:51:57.391212
- **Current Status**: `cancelled`
- **Finished**: 2026-03-31T23:01:58.350177
- **Duration**: ~10 minutes (properly timed out)

### Root Cause Analysis
1. **Timeout Mechanism Works Correctly**: 
   - Worker has `job_timeout_seconds` setting = 600s (10 minutes)
   - Job 1647 was cancelled after 10 minutes (correct behavior)
   - Worker called `expire_timed_out_jobs()` which properly cancelled the job

2. **Why Job Hung**:
   - Job 1647 started at 22:51:57
   - Worker was restarted at 23:01:34 (stop) → 23:01:37 (start)
   - Job was already running when worker restarted
   - Worker's timeout check ran at next loop iteration and cancelled it

3. **Subsequent Failures**:
   - Job 1652 failed with Ollama 500 error
   - Recent logs show "Connection refused" errors for both Ollama and Frigate
   - Camera last_status shows Ollama HTTP 500 error

### System State
- **Worker**: Functioning correctly with proper timeout handling
- **Job Queue**: Jobs being processed and timed out appropriately
- **Ollama**: API responding (checked with `/api/tags`) but intermittent 500 errors on `/api/chat`
- **Frigate**: Connection refused errors (192.168.88.97 may be unreachable or service down)

### Recent Jobs for camera_88_4 (id=12)
```
1652 | failed    | Ollama 500 error
1647 | cancelled | Timed out (600s) ← Issue job
1646 | cancelled | Cancelled by user
1645 | success   | Normal completion
1644 | success   | Normal completion
```

## Changed files
- None (analysis only, no code changes)

## Decisions
- **No code changes needed**: Worker timeout mechanism is working correctly
- **Job 1647 behavior is expected**: It was properly cancelled after 10-minute timeout
- **Real issue**: Intermittent Ollama 500 errors and Frigate connection issues

## Verification
- Checked database: Job 1647 status = `cancelled`, finished_at set correctly
- Checked worker logs: Timeout mechanism triggered appropriately
- Checked Ollama API: Responding but returning 500 errors on chat endpoint
- Checked Frigate: Connection refused errors

## Risks / Follow-ups
1. **Intermittent Ollama errors**: Model `qwen3.5:2b` returning 500 errors sporadically
   - May need model reload or different model selection
   - Consider adding retry logic for transient 500 errors
   
2. **Frigate connectivity**: Connection refused to 192.168.88.97
   - Check if Frigate service is running
   - Verify network connectivity
   - May need Frigate restart

3. **Job visibility in UI**: "Running indefinitely" perception
   - Consider adding real-time job status updates to frontend
   - Show elapsed time for running jobs
   - Display timeout threshold in UI

## Resume point
- Issue #1647 resolved (analysis complete)
- Recommended next steps:
  1. Monitor Ollama `/api/chat` endpoint for 500 errors
  2. Check Frigate service status on 192.168.88.97
  3. Consider adding retry logic for transient inference errors
  4. Improve UI to show job progress and timeout countdown
