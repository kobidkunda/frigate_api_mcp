# TODOs

## In Progress
- [ ] Camera management: add/edit/test/save/delete, and robust Frigate snapshot
  - Owner: agent
  - Started: 2026-03-28
  - Related: docs/plans/2026-03-28-camera-management-design.md, docs/implementation/2026-03-28-camera-management.md
  - Next step: verify snapshot timeout/auth settings; confirm Delete flow end-to-end
- [ ] Group analytics foundation: groups and camera membership API
  - Owner: agent
  - Started: 2026-03-28
  - Related: docs/plans/2026-03-28-group-analytics-and-merged-scenes-plan.md, docs/implementation/2026-03-28-group-analytics.md
  - Next step: persist group analysis into rollups and complete group-aware processed-events/charts summaries
- [ ] Harden frontend init to avoid null element access
  - Owner: agent
  - Started: 2026-03-28
  - Related: docs/implementation/2026-03-28-ui-errors-null-elements-and-favicon.md
  - Next step: add smoke tests for each page's init path
## Planned
- [ ] Add page-level smoke tests for Charts and Reports rendering
  - Related: docs/implementation/2026-03-28-ui-ux-a11y-hardening-and-tests.md
  - Next step: extend tests for empty states and error states

## Blocked

## Done
- [x] UI/UX improvements baseline and accessibility
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-ui-ux-a11y-hardening-and-tests.md
