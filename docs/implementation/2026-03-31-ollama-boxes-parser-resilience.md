# 2026-03-31 - Ollama boxes parser resilience

## Summary
The `qwen3.5:2b` model (and sometimes `qwen3.5:9b`) returns malformed or missing `boxes` payloads, causing RuntimeError "invalid boxes payload" that kills analysis jobs (e.g. Job #1494). Made the parser resilient instead of failing hard.

## Why
- Small vision models inconsistently follow the JSON schema prompt
- Missing `boxes` key, pixel coordinates (>1.0), non-list values, and wrong labels all caused hard failures
- These failures wasted entire analysis cycles on recoverable responses

## Scope
- `factory_analytics/integrations/ollama.py` - `_parse_classification_content` method

## Changes
1. **Missing/non-list `boxes`**: Default to `[]` with a warning instead of raising RuntimeError (was only defaulting for group mode)
2. **Non-object box entries**: Skip with warning instead of crashing
3. **Non-person labels**: Skip with warning instead of crashing
4. **Invalid box coordinates (<4 values)**: Skip with warning instead of crashing
5. **Non-numeric coordinates**: Skip the box with warning instead of crashing
6. **Pixel coordinates (>1.0)**: Auto-normalize by dividing by max value, then clamp to 0-1

## Changed files
- `factory_analytics/integrations/ollama.py` - Lines 147-204: replaced hard errors with warnings + graceful fallback

## Decisions
- Normalize pixel coordinates by max value rather than crashing (no image dimensions available in parser)
- Log warnings for every skipped box so debugging is still possible
- Clamp final values to [0,1] to prevent downstream rendering errors

## Verification
- Syntax check passed: `python3 -c "import py_compile; py_compile.compile('factory_analytics/integrations/ollama.py', doraise=True)"`
- No pytest available in environment to run unit tests

## Risks
- Pixel normalization is approximate (divides by max coordinate, not image width/height)
- Consider switching to a larger model (9b+) for more reliable JSON output
