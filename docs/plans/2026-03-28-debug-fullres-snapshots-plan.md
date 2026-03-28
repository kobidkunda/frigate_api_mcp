# Debug Full-Resolution Snapshots Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the current `./factory-analytics.sh debug` failures and ensure the app always sends full-resolution Frigate snapshots to the LLM while keeping UI thumbnails display-sized only.

**Architecture:** Preserve the existing capture -> analysis -> evidence flow, but remove capture-time downscaling so the saved snapshot and the image sent into Ollama are the same full-resolution asset. Diagnose the debug command by reproducing the current failure, then add failing tests for each confirmed bug before making the smallest corrective changes in the shell script or Python services.

**Tech Stack:** Bash, FastAPI, Python, pytest, httpx, Pillow.

---

### Task 1: Reproduce debug startup failure

**Files:**
- Modify: `progress.md`
- Modify: `findings.md`

**Step 1: Run the failing command**

Run: `./factory-analytics.sh debug`

**Step 2: Capture the exact traceback or log output**

- Record the first failing error in `findings.md`
- Record the command result in `progress.md`

**Step 3: Verify the failing component**

Run: `./factory-analytics.sh status`

**Step 4: Commit**

```bash
git add findings.md progress.md
git commit -m "docs(debug): capture debug startup failure evidence"
```

### Task 2: Lock in full-resolution snapshot behavior with tests

**Files:**
- Modify: `tests/test_image_composition.py`
- Create or Modify: `tests/test_frigate_integration.py`
- Modify: `factory_analytics/integrations/frigate.py`

**Step 1: Write the failing test**

Add a test asserting `fetch_latest_snapshot()` does not append resize or quality query parameters to the requested Frigate URL.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_frigate_integration.py -v`
Expected: FAIL because current code appends `h=720&quality=70`.

**Step 3: Write minimal implementation**

- Remove the capture-time scaling query string from Frigate snapshot fetches
- Preserve endpoint fallback order only if still required by current Frigate behavior

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_frigate_integration.py -v`

**Step 5: Commit**

```bash
git add tests/test_frigate_integration.py factory_analytics/integrations/frigate.py
git commit -m "fix(frigate): use full-resolution snapshots for analysis"
```

### Task 3: Add regression tests for the confirmed debug failure

**Files:**
- Modify: `tests/...` matching the confirmed failing component
- Modify: `factory-analytics.sh` or the failing Python module

**Step 1: Write the failing test first**

- Use the exact reproduced failure mode
- Prefer a targeted unit/integration test over a broad end-to-end test

**Step 2: Run test to verify it fails**

Run the narrowest `pytest` selection for the new test.

**Step 3: Write minimal implementation**

- Fix only the confirmed root cause
- Do not add fallback logic that changes feature behavior

**Step 4: Run the targeted test again**

Expected: PASS

**Step 5: Commit**

```bash
git add tests factory-analytics.sh factory_analytics
git commit -m "fix(debug): resolve reproduced startup failure"
```

### Task 4: Verify analysis and debug flow end-to-end

**Files:**
- Modify: `progress.md`
- Modify: `docs/implementation/2026-03-28-debug-fullres-snapshots.md`
- Modify: `docs/todos.md`
- Modify: `docs/features.md`

**Step 1: Run focused tests**

Run: `pytest tests/test_frigate_integration.py tests/test_ollama_integration.py tests/test_image_annotations.py tests/test_image_composition.py -v`

**Step 2: Run the real startup flow**

Run: `./factory-analytics.sh debug`

**Step 3: Confirm there are no remaining startup errors**

- Check `logs/api.log`
- Check `logs/mcp.log`
- Check `./factory-analytics.sh status`

**Step 4: Update durable memory**

- Implementation note with root cause, changed files, and verification
- `docs/todos.md` with final task state and next step if anything remains
- `docs/features.md` with full-resolution evidence status

**Step 5: Commit**

```bash
git add progress.md docs/implementation/2026-03-28-debug-fullres-snapshots.md docs/todos.md docs/features.md
git commit -m "docs(debug): record full-resolution snapshot and debug verification"
```
