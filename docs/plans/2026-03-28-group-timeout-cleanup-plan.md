# Group Timeout Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make real merged group analysis survive longer inference time and ensure timed-out group jobs are marked failed instead of being left in `running`.

**Architecture:** Keep full-resolution merged group images, but add group-specific timeout handling around the group Ollama path. On timeout or other exceptions during group analysis, mark the group job as failed immediately so history and retries stay truthful.

**Tech Stack:** Python, httpx, pytest, SQLite.

---

### Task 1: Lock in timeout cleanup with a failing test

**Files:**
- Modify: `tests/test_group_analysis.py`
- Test: `tests/test_group_analysis.py`

**Step 1: Write the failing test**

Add a test where group analysis raises a timeout and assert the created `group_analysis` job is marked `failed`, not left `running`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_group_analysis.py::test_group_run_timeout_marks_job_failed -v`
Expected: FAIL because current group run leaves the job in `running` on exception.

### Task 2: Implement group timeout cleanup

**Files:**
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/integrations/ollama.py` (only if a dedicated longer group timeout hook is needed)
- Modify: `tests/test_group_analysis.py`

**Step 1: Ensure group exceptions fail the job**

- Wrap the post-job-creation group pipeline in `try/except`
- On any exception, mark the group job failed with the real error message

**Step 2: Add group-specific longer timeout if needed**

- Keep camera analysis behavior unchanged
- Allow merged group calls to use a longer timeout path without changing original-resolution merge behavior

**Step 3: Run focused tests**

Run: `pytest tests/test_group_analysis.py -v`

### Task 3: Verify against `machine run test`

**Files:**
- Modify: `progress.md`
- Modify: `docs/implementation/2026-03-28-debug-fullres-snapshots.md`

**Step 1: Re-run the real group**

- Confirm the job either succeeds with persisted output, or fails cleanly instead of staying `running`

**Step 2: Record outcome**

- Update durable docs with the actual timeout behavior and result
