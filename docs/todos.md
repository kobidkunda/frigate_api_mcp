# TODOs

## In Progress
- [ ] Debug startup and enforce full-resolution LLM snapshots
  - Owner: agent
  - Started: 2026-03-28
  - Related: docs/plans/2026-03-28-debug-fullres-snapshots-plan.md, docs/implementation/2026-03-28-debug-fullres-snapshots.md
  - Next step: decide whether to drain/reset historical pending jobs and whether to harden Ollama retry/queue handling for real upstream 500/timeout responses
- [ ] Group analytics foundation: groups and camera membership API
  - Owner: agent
  - Started: 2026-03-28
  - Related: docs/plans/2026-03-28-group-analytics-and-merged-scenes-plan.md, docs/implementation/2026-03-28-group-analytics.md
  - Next step: persist group analysis into rollups and refine how group history is distinguished from anchor-camera-backed records in UI/reporting
- [ ] Service script: make stop work for debug sessions
  - Owner: agent
  - Started: 2026-03-28
  - Related: docs/implementation/2026-03-28-factory-analytics-sh-debug-stop-fix.md
  - Next step: verify on macOS and Linux; extend status fallback
## Planned
- [ ] Add page-level smoke tests for Charts and Reports rendering
  - Related: docs/implementation/2026-03-28-ui-ux-a11y-hardening-and-tests.md
  - Next step: extend tests for empty states and error states

## Blocked

## Done
- [x] Fix layout viewport overflow and redundant `<main>` tags
  - Done: 2026-03-29
  - Related: docs/implementation/2026-03-29-layout-overflow-fix.md
- [x] Stitch UI/UX design refresh
  - Done: 2026-03-29
  - Related: docs/implementation/2026-03-29-stitch-update.md
- [x] Group serial processing with configurable intervals
  - Done: 2026-03-29
  - Related: docs/plans/2026-03-29-group-serial-processing-plan.md, docs/implementation/2026-03-29-group-serial-processing.md
- [x] Add Control Center and API Explorer pages with metadata endpoints
  - Done: 2026-03-28
  - Related: docs/plans/2026-03-28-control-center-and-api-explorer-plan.md, docs/implementation/2026-03-28-debug-fullres-snapshots.md
- [x] Distinguish persisted merged group results explicitly in History and Processed views
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-debug-fullres-snapshots.md
- [x] Add LLM response hooks to History and continue group merges when some grouped cameras fail
  - Done: 2026-03-28
  - Related: docs/plans/2026-03-28-history-llm-and-group-merge-plan.md, docs/implementation/2026-03-28-debug-fullres-snapshots.md
- [x] Persist group merged-analysis results into durable history records
  - Done: 2026-03-28
  - Related: docs/plans/2026-03-28-history-llm-and-group-merge-plan.md, docs/implementation/2026-03-28-debug-fullres-snapshots.md
- [x] Show inline clickable evidence photos on History page
  - Done: 2026-03-28
  - Related: docs/plans/2026-03-28-history-photo-preview-plan.md, docs/implementation/2026-03-28-debug-fullres-snapshots.md
- [x] Camera management: add/edit/test/save/delete - delete flow verified end-to-end
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-camera-management.md
  - Verified: DELETE /api/cameras/{id} and POST fallback work; frontend deleteCamera() properly wired
- [x] Harden frontend init to avoid null element access - null checks already in place
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-ui-errors-null-elements-and-favicon.md
  - Verified: refreshAll() has defensive null checks; UI smoke tests exist in test_ui_ux.py
- [x] Prevent duplicate scheduler backlog and switch LLM input to full-resolution go2rtc frames
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-debug-fullres-snapshots.md
- [x] Fix app.js syntax error breaking global functions
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-fix-appjs-syntax.md
- [x] UI/UX improvements baseline and accessibility
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-ui-ux-a11y-hardening-and-tests.md
