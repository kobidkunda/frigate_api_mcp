# 2026-03-31 - Worker Efficiency Analytics with Calendar Heatmap

## Summary
Create a comprehensive worker efficiency analytics page with calendar heatmap visualization showing per-minute efficiency data with color-coded status indicators (working, idle, offline). Features shift-wise data display (day/night), date/weekly/monthly view toggles, and robust filtering capabilities.

## Scope
- Worker Efficiency page template
- Calendar heatmap component with color-coded cells
- Per-minute efficiency data aggregation
- Shift-wise data display (day/night)
- Date/weekly/monthly view toggle
- Status color indicators (working=green, idle=yellow, offline=gray)
- API endpoints for efficiency data with filtering
- Sidebar navigation update

## Changed files
- factory_analytics/templates/efficiency.html - New worker efficiency analytics page
- factory_analytics/static/efficiency.js - Calendar heatmap and data visualization
- factory_analytics/main.py - Add API endpoints for efficiency data
- factory_analytics/database.py - Add efficiency data queries
- factory_analytics/templates/partials/sidebar.html - Add navigation link

## Design Decisions
- Use modular grid-based calendar heatmap for easy date navigation
- Color scheme: working (#22c55e), idle (#eab308), offline (#6b7280), error (#ef4444)
- Shift boundaries: Day (06:00-18:00), Night (18:00-06:00)
- Data aggregation at minute-level for precision
- Responsive design for mobile and desktop

## API Design
- GET /api/efficiency/summary?from&to&view=daily|weekly|monthly
- GET /api/efficiency/heatmap?date&worker_id
- GET /api/efficiency/shifts?date&shift=day|night

## Resume point
Completed worker efficiency analytics page with calendar heatmap

## Verification
- ✓ All Python files pass syntax validation
- ✓ API endpoints added and functional
- ✓ Database queries optimized for per-minute granularity
- ✓ Frontend with responsive calendar heatmap
- ✓ Color-coded status indicators
- ✓ Shift-wise data display (day/night)
- ✓ Daily/Weekly/Monthly view toggles
- ✓ Camera and shift filtering
- ✓ Summary cards and top performers
- ✓ Activity log with pagination
- ✓ CSV export functionality
