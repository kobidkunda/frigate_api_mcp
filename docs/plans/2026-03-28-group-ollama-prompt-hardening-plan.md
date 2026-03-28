# Group Ollama Prompt Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make real merged group analysis resilient by using a stricter group-specific prompt and rejecting/retrying non-factory HTML/article-style model responses.

**Architecture:** Keep camera classification behavior unchanged, but introduce a dedicated group-analysis prompt that explicitly describes a merged multi-camera factory collage and demands strict JSON output. Add targeted validation for known garbage-response patterns and a narrow retry path for group analyses only.

**Tech Stack:** Python, httpx, pytest.

---

### Task 1: Lock in failure reproduction with a test

**Files:**
- Modify: `tests/test_ollama_integration.py`
- Test: `tests/test_ollama_integration.py`

**Step 1: Write the failing test**

Add a test where the model returns JSON-wrapped HTML/article content and assert group-analysis classification rejects it as non-factory garbage rather than treating it like a normal invalid boxes error.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ollama_integration.py::test_classify_group_image_rejects_html_article_payload -v`
Expected: FAIL because the current parser has no group-specific handling and treats it generically.

**Step 3: Write minimal implementation**

Do not implement yet.

### Task 2: Add group-specific prompt and retry path

**Files:**
- Modify: `factory_analytics/integrations/ollama.py`
- Modify: `factory_analytics/services.py`
- Modify: `tests/test_ollama_integration.py`

**Step 1: Add a dedicated group prompt**

- Describe the input as a merged multi-camera factory collage
- Emphasize: analyze only visible factory scenes, ignore any unrelated textual hallucinations, return JSON only

**Step 2: Add group classification entry point**

- Keep camera classification method unchanged if possible
- Add a group-specific method or explicit prompt path

**Step 3: Harden validation for garbage content**

- Detect HTML/article-shaped payloads
- Raise a clearer error for non-factory/non-JSON-contract responses

**Step 4: Add a narrow retry for group analysis only**

- Retry once with the strict group prompt if the first group response is garbage

**Step 5: Run targeted tests**

Run: `pytest tests/test_ollama_integration.py -v`

### Task 3: Verify against the real `machine run test` group

**Files:**
- Modify: `progress.md`
- Modify: `docs/implementation/2026-03-28-debug-fullres-snapshots.md`

**Step 1: Run a real group analysis**

Use the actual `machine run test` group and confirm the merged image now produces a valid classification response.

**Step 2: Verify persisted output**

- Confirm a new persisted group job/segment exists
- Confirm evidence image exists on disk

**Step 3: Update durable docs**

- Record the raw-response root cause and the prompt-hardening fix
