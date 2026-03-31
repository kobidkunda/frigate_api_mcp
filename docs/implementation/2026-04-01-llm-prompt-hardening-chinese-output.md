# 2026-04-01 - LLM Prompt Hardening for Chinese Output Issue

## Summary
Job #1662 failed because `qwen3.5:2b` returned Chinese text instead of JSON. Updated both DEFAULT_PROMPT and GROUP_PROMPT with strict JSON-only enforcement and explicit false positive warnings.

## Why
- Small vision models (qwen2.5-vl:2b, qwen3.5:2b) sometimes ignore JSON format instructions
- Previous prompts didn't explicitly forbid non-JSON output
- Factory scenes have many false positive objects (cloth, sacks, chairs) that models confuse with people

## Scope
- Updated DEFAULT_PROMPT with strict CCTV auditor persona
- Updated GROUP_PROMPT with same strict instructions
- Added explicit "Return ONLY valid JSON" instruction
- Added common false positives list to prevent misclassification

## Changed files
- `factory_analytics/integrations/ollama.py` - Updated DEFAULT_PROMPT and GROUP_PROMPT with stricter JSON enforcement and false positive warnings

## Decisions
- Adopted recommended "strict factory CCTV vision auditor" persona
- Added explicit CRITICAL RULES section with 7 numbered rules
- Listed common factory false positives (cloth bundles, sacks, chairs, etc.)
- Added "DO NOT include any text before or after the JSON" instruction

## Verification
- App restart required to pick up prompt changes
- Test with same camera that triggered #1662

## Risks / Follow-ups
- If Chinese output persists, may need model-level temperature/format enforcement
- Consider adding format: json to Ollama API payload (already present)
- May need to switch to larger model for better instruction following

## Resume point
Restart the application and trigger analysis on camera that produced Chinese output in #1662.
