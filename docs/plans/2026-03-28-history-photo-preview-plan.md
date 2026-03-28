# History Photo Preview Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show an inline photo on the History page and let users open the full saved evidence image from that preview.

**Architecture:** Keep the History page using the existing evidence path returned by the API, but replace the text `view` link with a larger inline image preview in both table and mobile card layouts. Use the same saved full-resolution evidence file as the preview source and wrap the image in a link so clicking it opens the original image.

**Tech Stack:** FastAPI templates, vanilla JavaScript, pytest.

---

### Task 1: Lock in the History page expectation with a failing test

**Files:**
- Modify: `tests/test_ui_ux.py`
- Test: `tests/test_ui_ux.py`

**Step 1: Write the failing test**

Add a test asserting the History page markup contains inline image preview behavior rather than only a text `view` link placeholder.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_history_page_renders_inline_evidence_preview_hooks -v`
Expected: FAIL because the template still renders `view` links only.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Commit**

```bash
git add tests/test_ui_ux.py
git commit -m "test(history): require inline evidence preview hooks"
```

### Task 2: Render larger inline evidence previews on History

**Files:**
- Modify: `factory_analytics/templates/history.html`
- Modify: `tests/test_ui_ux.py`

**Step 1: Replace text links with preview markup**

- In desktop rows, render a clickable `<img>` using `s.evidence_path`
- In mobile cards, render the same preview pattern
- Keep the target as the original evidence image in a new tab/full view

**Step 2: Keep the preview larger but bounded**

- Use inline style or template-local classes sized for readability without exploding the table layout

**Step 3: Run test to verify it passes**

Run: `pytest tests/test_ui_ux.py::test_history_page_renders_inline_evidence_preview_hooks -v`

**Step 4: Commit**

```bash
git add factory_analytics/templates/history.html tests/test_ui_ux.py
git commit -m "feat(history): show clickable inline evidence previews"
```

### Task 3: Verify and update durable memory

**Files:**
- Modify: `docs/implementation/2026-03-28-debug-fullres-snapshots.md`
- Modify: `docs/todos.md`
- Modify: `docs/features.md`
- Modify: `progress.md`

**Step 1: Run focused verification**

Run: `pytest tests/test_ui_ux.py -v`

**Step 2: Update docs**

- Record the History page photo-preview behavior
- Note that History now shows inline evidence thumbnails with click-to-open full image

**Step 3: Commit**

```bash
git add docs/implementation/2026-03-28-debug-fullres-snapshots.md docs/todos.md docs/features.md progress.md
git commit -m "docs(history): record inline evidence preview behavior"
```
