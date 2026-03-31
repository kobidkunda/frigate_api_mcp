# 2026-03-30 - Remove raw_result from API output

## Summary
Remove the large `raw_result` object from API responses to reduce payload size and hide internal LLM metadata. Ensure `group_name` and other essential metadata are still present.

## Why
- The `raw_result` contains full LLM thinking process and large JSON blobs which are unnecessary for most frontend views.
- Reducing payload size improves performance.
- Internal metadata should be hidden from general API output.

## Scope
- Modify `database.py` to stop including `raw_result` in `get_segment`, `list_segments`, and `list_segments_paginated`.
- Verify `group_name`, `group_type`, and `group_id` are still extracted from `payload_json`.

## Changed files
- `factory_analytics/database.py`

## Decisions
- Use `payload_json` (which contains the same metadata for group jobs) instead of `raw_result` to populate group-related fields in listing methods.
- Explicitly pop `raw_result` in `get_segment` or don't select it at all.

## Verification
- Check API output for `raw_result` presence.
- Check API output for `group_name` presence.

## Resume point
- Modify `get_segment` in `factory_analytics/database.py` to remove `raw_result`.
