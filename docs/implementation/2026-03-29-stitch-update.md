# 2026-03-29 - Stitch UI Update

## Summary
Downloaded updated HTML files from Stitch project 6669821483591404996 and integrated them to update the UI and UX of all pages in the Factory Analytics application.

## Why
- Business reason: Update the UI and UX of the application using the latest "Industrial Sentinel" designs from Stitch, transitioning to a Tailwind CSS based layout.

## Scope
- Downloaded and saved the following screens to `static/`:
  - Factory Analytics Dashboard
  - Factory Analytics Settings
  - Factory Analytics Segments
- Integrated Tailwind CSS via CDN
- Updated all existing templates (`base.html`, `dashboard.html`, `settings.html`, `history.html`, `groups.html`, `logs.html`, `control_center.html`, `api_explorer.html`, `charts.html`, `processed_events.html`) to use the new UI components and layout.
- Created reusable partials (`top_nav.html`, `sidebar.html`, `tailwind_head.html`, `tailwind_config.html`).

## Changed files
- `factory_analytics/templates/partials/base.html` - Updated to include tailwind, new top nav, and sidebar.
- `factory_analytics/templates/partials/top_nav.html` - Created new top navigation bar based on Stitch design.
- `factory_analytics/templates/partials/sidebar.html` - Created new side navigation bar based on Stitch design.
- `factory_analytics/templates/partials/tailwind_head.html` - Added Tailwind CDN and font links.
- `factory_analytics/templates/partials/tailwind_config.html` - Added inline Tailwind configuration from Stitch design system.
- `factory_analytics/templates/dashboard.html` - Updated layout and components to match Stitch design.
- `factory_analytics/templates/settings.html` - Updated layout and components to match Stitch design.
- `factory_analytics/templates/history.html` - Updated layout and components based on the Segments design.
- `factory_analytics/templates/groups.html` - Updated layout and components to match the new style.
- `factory_analytics/templates/logs.html` - Updated layout and components to match the new style.
- `factory_analytics/templates/control_center.html` - Updated layout and components to match the new style.
- `factory_analytics/templates/api_explorer.html` - Updated layout and components to match the new style.
- `factory_analytics/templates/charts.html` - Updated layout and components to match the new style.
- `factory_analytics/templates/processed_events.html` - Updated layout and components to match the new style.
- `factory_analytics/templates/partials/mobile_bottom_nav.html` - Added for mobile navigation.

## Update - Mobile Support
- Added `mobile_bottom_nav.html` partial for mobile view.
- Updated `base.html` to be more responsive (added `md:ml-64`, removed fixed sidebar on mobile).
- Adjusted `top_nav.html` and `sidebar.html` visibility based on breakpoints.

## Decisions
- Used Tailwind CSS via CDN as it was provided in the Stitch export and is easy to integrate without a complex build step for this Python/FastAPI app.
- Extracted the Tailwind configuration into a partial so it can be reused across all pages.
- Adapted the static HTML from Stitch into dynamic Jinja2 templates, preserving the original functionality (e.g., JavaScript event listeners, API calls) while applying the new styling.

## Verification
- Verified all templates are updated and include the necessary Tailwind classes.

## Risks / Follow-ups
- Some custom Javascript functionality might need slight adjustments if class names or IDs were heavily relied upon, though effort was made to preserve them.
- Need to ensure responsive behavior is fully functional across all views.

## Resume point
- Verify UI visually by running the application.