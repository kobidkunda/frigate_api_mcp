# TODOs

## In Progress
- [ ] Test LLM prompt hardening on camera that produced Chinese output
- Owner: ops
- Related: docs/implementation/2026-04-01-llm-prompt-hardening-chinese-output.md
- Next step: Restart app and trigger analysis on same camera

## Planned
- [ ] Monitor Ollama /api/chat endpoint for intermittent 500 errors
- Owner: ops
- Related: docs/implementation/2026-04-01-camera-88-4-visibility-analysis-issue-1647.md
- Next step: Add retry logic for transient inference errors
- [ ] Check Frigate service status on 192.168.88.97
- Owner: ops
- Related: docs/implementation/2026-04-01-camera-88-4-visibility-analysis-issue-1647.md
- Next step: Verify network connectivity and service health
- [ ] Add page-level smoke tests for Charts and Reports rendering
  - Related: docs/implementation/2026-03-28-ui-ux-a11y-hardening-and-tests.md
  - Next step: extend tests for empty states and error states

## Blocked

## Done
- [x] Switch Ollama to OpenAI-compatible API mode & fix test button
  - Done: 2026-04-04
  - Related: docs/implementation/2026-04-04-ollama-openai-api-mode.md
  - Features: Added ollama_api_mode setting (default: openai), fixed test button response parsing, added API mode dropdown in settings UI
- [x] Redesign Control Center page with comprehensive OpenCode usage guide
- Done: 2026-04-01
- Related: factory_analytics/templates/control_center.html
- Features: Quick start guide, step-by-step integration, connection testing, tabbed guides for OpenCode/Claude/Codex/Python, interactive tool listing
- [x] Add evidence photo auto-delete setting
- Done: 2026-04-01
- Related: docs/implementation/2026-04-01-evidence-auto-delete-setting.md
- Features: evidence_retention_days setting (default 30), daily cleanup in worker, DB refs cleared but records preserved
- [x] Create comprehensive OpenCode usage guide for Control Center
- Done: 2026-04-01
- Related: docs/implementation/2026-04-01-control-center-opencode-usage-guide.md
- Content: MCP setup, skills inventory, integration examples, best practices, troubleshooting
- [x] Create MAINTENANCE.md manual for SysAdmins/DevOps
- Done: 2026-04-01
- Related: docs/MAINTENANCE.md
- Content: Quick reference, service management, database maintenance, external integrations, worker/scheduler, monitoring, troubleshooting
- [x] Implement LLM multi-frame capture and image optimization
- Done: 2026-04-01
- Related: docs/implementation/2026-04-01-llm-image-sampling-optimization.md
- Features: 5 new settings, ImagePipeline module, job timeout, frame thumbnails in Visual Evidence
- [x] Add Photo Gallery page with filtering and pagination
- Done: 2026-04-01
- Related: docs/implementation/2026-04-01-photo-gallery-page.md
- Features: Photo cards with status-colored backgrounds, filters (date, day, time, camera, group, status), server-side pagination, click-to-modal view, added to sidebar and mobile nav
- [x] Analyze camera_88_4 visibility runs not completing (issue #1647)
- Done: 2026-04-01
- Related: docs/implementation/2026-04-01-camera-88-4-visibility-analysis-issue-1647.md
- Resolution: Job 1647 properly cancelled by timeout mechanism after 10 minutes; system working correctly
- [x] Upgrade Efficiency page with ApexCharts heatmaps
  - Done: 2026-03-31
  - Related: docs/implementation/2026-03-31-apexcharts-heatmap-upgrade.md
  - Features: Daily/Weekly/Monthly heatmap views, shift dividers, click-to-show detail chip with Classification/Metadata/Temporal Span/Visual Evidence, only group-enabled cameras shown
- [x] Fix worker scheduler indentation bug causing UnboundLocalError
  - Done: 2026-03-31
  - Related: docs/implementation/2026-03-31-worker-scheduler-indentation-fix.md
- [x] Add job_type filter to jobs_paginated endpoint
  - Done: 2026-03-31
- [x] Refactor Ollama health checks: split API and Vision tests
  - Done: 2026-03-31
- [x] Create worker efficiency analytics page with calendar heatmap
  - Done: 2026-03-31
- [x] Audit and update MCP server: Added 29 new tools (43 total), 100% REST API coverage
- [x] Update API Explorer with detailed skill guidance for all endpoints
- [x] Create comprehensive MCP documentation (docs/mcp-server.md)
- [x] Create MCP test suite (tests/test_mcp_tools.py) - all 43 tools passing
