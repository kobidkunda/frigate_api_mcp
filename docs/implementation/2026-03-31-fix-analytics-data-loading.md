# 2026-03-31 - Fix Analytics Data Loading Error

## Summary
Fixed "Failed to load analytics data" error on history and logs pages by optimizing database queries and adding cache-busting to JavaScript.

## Why
- API responses were too large (549KB) causing browser timeouts
- `raw_result` and `payload_json` fields contained large JSON objects that weren't needed by the UI
- Browser cache was serving old JavaScript that expected removed fields

## Scope
- Optimized `list_segments` and `list_segments_paginated` in database.py
- Optimized `get_segment` in database.py
- Added cache-busting comments to history.html and logs.html

## Changed files
- `factory_analytics/database.py` - Removed `raw_result` from SELECT queries, only extract essential group metadata
- `factory_analytics/templates/history.html` - Added cache-bust comment
- `factory_analytics/templates/logs.html` - Added cache-bust comment

## Decisions
- **Decision**: Remove `raw_result` and `payload_json` from segment API responses
- **Alternative**: Add pagination with smaller page sizes
- **Why**: The UI only needs `group_name`, `group_type`, and `group_id` from the payload, not the entire raw_result JSON

## Verification
- API response size reduced from 549KB to ~13KB (42x improvement)
- `limit` and `offset` parameters now work correctly
- No `raw_result` or `payload_json` fields in API responses
- Cache-busting forces browser to reload JavaScript

## Testing
```bash
# Before: 549KB response with raw_result
curl -s "http://192.168.88.81:8090/api/history/segments?limit=1" | jq '.[0] | has("raw_result")'
# true

# After: 663 bytes response without raw_result
curl -s "http://192.168.88.81:8090/api/history/segments?limit=1" | jq '.[0] | has("raw_result")'
# false

# Verify pagination works
curl -s "http://192.168.88.81:8090/api/history/segments?limit=20" | jq length
# 20

# Verify response size
curl -s "http://192.168.88.81:8090/api/history/segments?limit=20" | wc -c
# 12953 bytes (vs 549196 before)
```

## Risks / Follow-ups
- None identified
- UI continues to work correctly with optimized responses
