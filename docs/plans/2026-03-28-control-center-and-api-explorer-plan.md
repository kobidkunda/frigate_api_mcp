# Control Center And API Explorer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Control Center page for read-only config inspection, MCP/API monitoring, and install instructions, plus an API Explorer page for endpoint catalog/testing and skill-usage guidance.

**Architecture:** Extend the existing FastAPI dashboard with two new HTML pages and supporting JSON endpoints. The Control Center will inspect real local config files and show live health/test status, while the API Explorer will derive its endpoint catalog from the running FastAPI app and provide safe endpoint testing plus usage guidance.

**Tech Stack:** FastAPI, Jinja templates, vanilla JS, pytest, local filesystem inspection.

---

### Task 1: Lock in new pages and metadata endpoints with failing tests

**Files:**
- Modify: `tests/test_ui_ux.py`
- Create or Modify: `tests/test_control_center_api.py`

**Step 1: Write failing page tests**

- Require `/control-center` to render
- Require `/api-explorer` to render

**Step 2: Write failing metadata endpoint tests**

- Require config inspection endpoint
- Require API catalog endpoint

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_ui_ux.py tests/test_control_center_api.py -v`

### Task 2: Implement Control Center page and backend metadata

**Files:**
- Modify: `factory_analytics/main.py`
- Create: `factory_analytics/templates/control_center.html`
- Create: `factory_analytics/static/control_center.js`
- Create or Modify: `factory_analytics/services.py` or a new helper module for config inspection

**Step 1: Add page route**

- `GET /control-center`

**Step 2: Add metadata/test endpoints**

- config files detected
- skill directories/files available
- MCP/API health and test status
- platform-specific install instruction payload

**Step 3: Keep read-only semantics**

- no config mutation
- mask sensitive values

**Step 4: Run focused tests**

Run: `pytest tests/test_control_center_api.py -v`

### Task 3: Implement API Explorer page and endpoint catalog

**Files:**
- Modify: `factory_analytics/main.py`
- Create: `factory_analytics/templates/api_explorer.html`
- Create: `factory_analytics/static/api_explorer.js`
- Create or Modify: helper code for route catalog generation

**Step 1: Add page route**

- `GET /api-explorer`

**Step 2: Add API catalog endpoint**

- enumerate methods, paths, grouped categories, descriptions
- add safe endpoint testing metadata
- add skill-usage notes

**Step 3: Run focused tests**

Run: `pytest tests/test_control_center_api.py tests/test_ui_ux.py -v`

### Task 4: Add navigation and verify end-to-end UX

**Files:**
- Modify: relevant templates such as `dashboard.html`, `index.html`, and shared nav markup in existing templates
- Modify: `tests/test_ui_ux.py`

**Step 1: Add links to new pages**

- Keep navigation consistent with current pages

**Step 2: Verify render and basic usability**

- page titles
- key hooks present
- API endpoints return structured JSON

### Task 5: Update durable docs

**Files:**
- Modify: `docs/implementation/2026-03-28-debug-fullres-snapshots.md`
- Modify: `docs/features.md`
- Modify: `docs/todos.md`
- Modify: `progress.md`

**Step 1: Record feature and verification**

- Control Center capabilities
- API Explorer capabilities
- config inspection safety rules
