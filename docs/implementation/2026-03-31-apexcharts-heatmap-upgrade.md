# 2026-03-31 - ApexCharts Heatmap Upgrade

## Summary
Upgraded the Efficiency page from custom CSS grid heatmaps to ApexCharts library. Added Daily/Weekly/Monthly views with shift dividers, click-to-show detail chips, and filtering to only show group-enabled cameras.

## Why
- Custom CSS grid heatmap was limited and hard to maintain
- User requested ApexCharts for better visualization
- Need shift divider lines at 06:00 and 18:00 for day/night distinction
- Need click-to-show detail chip with Classification, Metadata, Temporal Span, Visual Evidence
- Only enabled cameras in groups should be shown

## Changed files
- `factory_analytics/templates/efficiency.html` - Complete rewrite with ApexCharts containers, popover, legend
- `factory_analytics/static/efficiency.js` - Complete rewrite with ApexCharts heatmap rendering, 3 views, click handlers
- `factory_analytics/database.py` - Added `efficiency_heatmap_chart()` method with group-camera filtering
- `factory_analytics/main.py` - Added `/api/efficiency/heatmap-chart` endpoint
- `factory_analytics/services.py` - Added `efficiency_heatmap_chart()` service method

## Key features
- **Daily view**: 24h heatmap per camera+group, shift dividers at 06:00 and 18:00
- **Weekly view**: 7 days heatmap per camera+group
- **Monthly view**: 30 days heatmap per camera+group, zoomable with toolbar
- **Click detail chip**: Shows Classification (label), Metadata (confidence, segments, minutes), Temporal Span, Visual Evidence link, and link to log details page
- **Group-only cameras**: Only enabled cameras in groups are shown (camera_88_2 and camera_88_4 from "machine run test")
- **Color scale**: Working (green), Idle (yellow), Operator Missing (orange), Stopped (red), No Data (gray)

## Bug fix
- Fixed `loadData()` setting `state.isLoading = true` before calling `refreshData()`, which caused `refreshData()` to exit immediately due to its `if (state.isLoading) return;` guard.

## Verification
- Tested via Playwright browser - page loads, heatmap renders, data loads correctly
- Summary cards show: 17% efficiency, 0:50 working time, 1:55 idle time, 5 active workers
- Heatmap shows 2 camera+group rows with 24 hour columns
- Shift dividers visible at 06:00 (Day Shift) and 18:00 (Night Shift)
- Activity log shows 50 entries with pagination
