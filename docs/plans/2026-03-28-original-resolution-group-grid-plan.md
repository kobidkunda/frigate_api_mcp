# Original Resolution Group Grid Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild merged group photos so every included source image is preserved at original resolution in a grid layout with no scaling.

**Architecture:** Replace the current fixed tile-size compositor with a grid that sizes each column and row from the actual source image dimensions. The final canvas grows to fit the originals, and each image is pasted at native size with only a small label overlay.

**Tech Stack:** Python, Pillow, pytest.

---

### Task 1: Lock in no-scaling merge expectations with a failing test

**Files:**
- Modify: `tests/test_image_composition.py`
- Test: `tests/test_image_composition.py`

**Step 1: Write the failing test**

Add a test with differently sized source images and assert the merged output is large enough to preserve each image at original dimensions within the final grid layout.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_image_composition.py::test_merge_group_snapshots_preserves_original_dimensions_in_grid -v`
Expected: FAIL because current compositor forces a uniform max tile size grid instead of a true original-dimension layout.

**Step 3: Write minimal implementation**

Do not implement yet.

**Step 4: Commit**

```bash
git add tests/test_image_composition.py
git commit -m "test(images): require original-resolution group grid layout"
```

### Task 2: Implement original-resolution group grid compositor

**Files:**
- Modify: `factory_analytics/image_composition.py`
- Modify: `tests/test_image_composition.py`

**Step 1: Build row/column sizing from actual image sizes**

- Keep grid layout
- Do not resize any source image
- Compute row heights and column widths from the images placed in each row/column

**Step 2: Paste originals without scaling**

- Keep each image at native width/height
- Keep labels as overlays only

**Step 3: Run the focused test**

Run: `pytest tests/test_image_composition.py::test_merge_group_snapshots_preserves_original_dimensions_in_grid -v`

**Step 4: Run the image composition file**

Run: `pytest tests/test_image_composition.py -v`

**Step 5: Commit**

```bash
git add factory_analytics/image_composition.py tests/test_image_composition.py
git commit -m "fix(images): preserve original resolution in group grid merge"
```

### Task 3: Update durable memory

**Files:**
- Modify: `docs/implementation/2026-03-28-debug-fullres-snapshots.md`
- Modify: `docs/features.md`
- Modify: `docs/todos.md`
- Modify: `progress.md`

**Step 1: Record the layout decision and verification**

- Note that group merged images use a no-scaling original-resolution grid

**Step 2: Commit**

```bash
git add docs/implementation/2026-03-28-debug-fullres-snapshots.md docs/features.md docs/todos.md progress.md
git commit -m "docs(images): record original-resolution group grid behavior"
```
