# History LLM Response And Group Merge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show LLM response details in History/processed views and make group merged analysis include all grouped cameras even when they are disabled for standalone runs, while continuing with available cameras if some snapshots fail.

**Architecture:** Preserve standalone camera scheduling rules based on `camera.enabled`, but treat group membership as the source of truth for merged group analysis. Extend group-run results to record included and missing cameras plus LLM notes, then render those details in History and processed-events views alongside the inline evidence photo.

**Tech Stack:** FastAPI, SQLite, vanilla JS, pytest, Pillow.

---

### Task 1: Lock in group merge inclusion rules with a failing test

**Files:**
- Modify: `tests/test_group_analysis.py`
- Test: `tests/test_group_analysis.py`

**Step 1: Write the failing test**

Add a test that creates a group with one enabled and one disabled camera, then asserts group analysis still attempts to include both group members rather than filtering by standalone `enabled`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_group_analysis.py::test_group_run_includes_grouped_disabled_cameras -v`
Expected: FAIL because current group logic does not record this behavior and may abort on the first snapshot failure.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Commit**

```bash
git add tests/test_group_analysis.py
git commit -m "test(groups): require grouped disabled cameras in merged analysis"
```

### Task 2: Lock in partial-merge behavior with a failing test

**Files:**
- Modify: `tests/test_group_analysis.py`
- Test: `tests/test_group_analysis.py`

**Step 1: Write the failing test**

Add a test asserting that if one group camera snapshot fails, the group run continues with available snapshots and records the missing camera name.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_group_analysis.py::test_group_run_continues_with_missing_camera_note -v`
Expected: FAIL because current implementation fails immediately on snapshot errors and does not return missing-camera metadata.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Commit**

```bash
git add tests/test_group_analysis.py
git commit -m "test(groups): require partial merged analysis with missing camera notes"
```

### Task 3: Lock in History UI support for LLM response text

**Files:**
- Modify: `tests/test_ui_ux.py`
- Test: `tests/test_ui_ux.py`

**Step 1: Write the failing test**

Add a test asserting the History page template contains hooks/classes for rendering LLM notes/response details near the evidence preview.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_history_page_renders_llm_response_hooks -v`
Expected: FAIL because current template only renders label/confidence and photo preview.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Commit**

```bash
git add tests/test_ui_ux.py
git commit -m "test(history): require llm response display hooks"
```

### Task 4: Implement group merge metadata and partial-merge behavior

**Files:**
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/database.py` (only if extra persistence is needed)
- Modify: `tests/test_group_analysis.py`

**Step 1: Include all grouped cameras regardless of standalone enabled state**

- Keep `list_group_cameras(group_id)` as the source for merge candidates
- Do not filter by `camera.enabled` in group runs

**Step 2: Continue when some camera snapshots fail**

- Attempt all group member snapshots
- Build merged image from successful captures only
- Record `included_cameras` and `missing_cameras`
- If all captures fail, fail the group run honestly

**Step 3: Carry LLM notes and merge metadata in the response**

- Include `notes`
- Include included/missing camera names
- Include camera counts based on actual included snapshots

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_group_analysis.py -v`

**Step 5: Commit**

```bash
git add factory_analytics/services.py tests/test_group_analysis.py factory_analytics/database.py
git commit -m "feat(groups): support partial merged analysis with missing camera tracking"
```

### Task 5: Render LLM response details in History and processed events

**Files:**
- Modify: `factory_analytics/templates/history.html`
- Modify: `factory_analytics/static/processed_events.js`
- Modify: `tests/test_ui_ux.py`

**Step 1: Add History rendering hooks**

- Render `notes` under the main label/confidence area
- When available, render included/missing group camera summary

**Step 2: Add processed-events rendering hooks**

- Show the same LLM notes/summary in processed segments view

**Step 3: Keep photo preview behavior intact**

- Do not regress the clickable inline photo preview already added

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui_ux.py -v`

**Step 5: Commit**

```bash
git add factory_analytics/templates/history.html factory_analytics/static/processed_events.js tests/test_ui_ux.py
git commit -m "feat(history): show llm response details for history and processed events"
```

### Task 6: Update durable memory and verify focused flows

**Files:**
- Modify: `docs/implementation/2026-03-28-debug-fullres-snapshots.md`
- Modify: `docs/features.md`
- Modify: `docs/todos.md`
- Modify: `progress.md`

**Step 1: Run final focused verification**

Run: `pytest tests/test_group_analysis.py tests/test_ui_ux.py -v`

**Step 2: Update docs**

- Record group merge inclusion rules
- Record missing-camera continuation behavior
- Record History/processed LLM response display behavior

**Step 3: Commit**

```bash
git add docs/implementation/2026-03-28-debug-fullres-snapshots.md docs/features.md docs/todos.md progress.md
git commit -m "docs(groups): record history llm details and merge rules"
```
