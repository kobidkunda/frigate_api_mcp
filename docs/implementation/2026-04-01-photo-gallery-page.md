# 2026-04-01 - Photo Gallery Page

## Summary
New page displaying all segment evidence photos as beautiful cards with status-colored backgrounds, filtering capabilities (date, day, time, camera, group, status), and server-side pagination.

## Why
- Visual evidence archive needs dedicated gallery view
- Users want to browse photos with classification metadata at a glance
- Filter by multiple dimensions for investigation/review workflows
- Beautiful card layout with status colors for quick visual scanning

## Scope
- New `/photos` route and template
- New `/api/photos` endpoint with filtering and pagination
- Photo cards with aspect-ratio preserved images
- Collapsible filter panel with date range, day of week, time range, camera/group/status multi-selects
- Server-side pagination (20 photos per page)
- Add menu item to sidebar and mobile nav

## Changed files
- `factory_analytics/database.py` - Add `list_photos_paginated()` method
- `factory_analytics/services.py` - Add `photos_paginated()` service method
- `factory_analytics/main.py` - Add `/photos` route and `/api/photos` endpoint
- `factory_analytics/templates/photos.html` - New page template
- `factory_analytics/static/photos.js` - Frontend JS for filtering/pagination
- `factory_analytics/templates/partials/sidebar.html` - Add "Photo Gallery" menu item
- `factory_analytics/templates/partials/mobile_bottom_nav.html` - Add to mobile nav

## Decisions
- Use aspect-ratio preserved card layout (not masonry, not fixed grid)
- Status colors: working=green, idle=gray, sleeping=purple, stopped=red, uncertain=dim
- Filters: date range, day of week (checkboxes), time range (slider), camera/group/status (multi-select)
- Page size: 20 photos
- Order by created_at DESC

## Verification
- Page loads and renders photo cards
- Filters work correctly
- Pagination works
- Status colors display correctly
- Click to view full-size photo

## Risks / Follow-ups
- Consider lazy loading for performance with large photo sets
- May need image thumbnail generation for very large evidence photos

## Resume point
Create database method first, then service, then API endpoint, then frontend templates.
