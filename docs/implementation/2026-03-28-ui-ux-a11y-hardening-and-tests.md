# 2026-03-28 - UI/UX A11y Hardening And Tests

## Summary
Add basic accessibility improvements (skip links, nav roles) to all main templates and introduce UI/UX smoke tests to guard regressions. Establish pytest config so the FastAPI app is importable in tests.

## Why
- Improve UX and accessibility for keyboard users.
- Create a test-driven baseline to validate pages render and contain key elements.
- User requested TDD approach and 100% completion.

## Scope
- Add `skip-link`, `role="navigation"`, and `role="main"` to dashboard, settings, history, and logs templates.
- Add pytest-based tests for page rendering and basic UI structure.
- Add `pytest.ini` to set `pythonpath=.`.
- Non-invasive; no business logic changes.

## Changed files
- `factory_analytics/templates/dashboard.html` – add skip link and ARIA roles.
- `factory_analytics/templates/settings.html` – add skip link and ARIA roles.
- `factory_analytics/templates/history.html` – add skip link and ARIA roles.
- `factory_analytics/templates/logs.html` – add skip link and ARIA roles.
- `factory_analytics/static/a11y.css` – dedicated accessibility helpers (skip link styles).
- `factory_analytics/static/theme.css` – design tokens (Blue accent) with light/dark support and focus outlines.
- `tests/test_ui_ux.py` – new tests for page render and elements.
- `pytest.ini` – configure pytest to discover tests and import app package.
- `factory_analytics/templates/partials/base.html` – new base layout template.
- `factory_analytics/templates/partials/nav.html` – shared header/navigation.
- `factory_analytics/templates/partials/secondary_tabs.html` – shared secondary tabs component.
- Converted dashboard/history/settings/logs to extend base layout.

## Decisions
- Minimal ARIA additions rather than full refactor to keep deltas small.
- Use FastAPI TestClient for speedy integration-style tests.
- Keep tests high-level to avoid flakiness from UI changes.

## Verification
- Ran `pytest -q` – 4 tests passed locally after each step.

## Risks / Follow-ups
- Add more granular tests for interactive behavior later.
- Consider adding Lighthouse/axe checks when browser-based testing is introduced.

## Resume point
- Next: expand UI per `data/features/mainaplication.md` navigation and add more UX tests for table interactions and forms.
- `factory_analytics/templates/logs.html` – add region states and aria-busy for logs loading.
- `factory_analytics/static/theme.css` – add actions row, states, pagination, nav button, KPI grid styles.
