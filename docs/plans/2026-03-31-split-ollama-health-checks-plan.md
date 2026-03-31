# Split Ollama Health Checks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor Ollama health checks into two distinct actions: API/Model verification and full Vision Inference (Snapshot + LLM).

**Architecture:** Add a new `AnalyticsService.test_ollama_api()` method and a corresponding `GET /api/settings/ollama/status` endpoint. Refactor the existing `test_ollama_vision()` to provide specific snapshot failure details. Update the Settings UI with two separate test buttons and results.

**Tech Stack:** FastAPI, httpx, vanilla JS, Jinja2.

---

### Task 1: Add Ollama API Health Service

**Files:**
- Modify: `factory_analytics/services.py`
- Test: `tests/test_ollama_health.py`

**Step 1: Write the failing test**

```python
def test_test_ollama_api_returns_model_status(service, client):
    # Mock OllamaClient.health to return a list including the vision model
    result = service.test_ollama_api()
    assert result['ok'] is True
    assert result['model_found'] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ollama_health.py -v`
Expected: FAIL because `test_ollama_api` is not defined.

**Step 3: Implement `test_ollama_api` in `AnalyticsService`**

```python
def test_ollama_api(self) -> dict[str, Any]:
    settings = self.settings()
    health = self.ollama_client().health()
    if not health.get("ok"):
        return {
            "ok": False,
            "message": f"Ollama unreachable: {health.get('message', 'unknown error')}",
        }
    model = settings.get("ollama_vision_model")
    models = set(health.get("models") or [])
    model_found = model in models
    return {
        "ok": True,
        "model_found": model_found,
        "message": "API reachable" + (f" (Model '{model}' found)" if model_found else f" (Model '{model}' NOT found)"),
        "available_models": list(models)
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ollama_health.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add factory_analytics/services.py tests/test_ollama_health.py
git commit -m "feat(services): add test_ollama_api for connectivity verification"
```

---

### Task 2: Add Ollama Status API Endpoint

**Files:**
- Modify: `factory_analytics/main.py`
- Test: `tests/test_api.py`

**Step 1: Write the failing test**

```python
def test_ollama_status_endpoint(client):
    response = client.get('/api/settings/ollama/status')
    assert response.status_code == 200
    assert 'model_found' in response.json()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_ollama_status_endpoint -v`
Expected: FAIL with 404.

**Step 3: Add the endpoint to `main.py`**

```python
@app.get(\"/api/settings/ollama/status\")
def get_ollama_status():
    return service.test_ollama_api()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_ollama_status_endpoint -v`
Expected: PASS

**Step 5: Commit**

```bash
git add factory_analytics/main.py tests/test_api.py
git commit -m "feat(api): add GET /api/settings/ollama/status endpoint"
```

---

### Task 3: Improve Vision Test Error Reporting

**Files:**
- Modify: `factory_analytics/services.py`

**Step 1: Refactor `test_ollama_vision` to be more specific**

Change the `_capture_snapshot` call to catch and report specific camera name and error.

**Step 2: Run manual verification**

(Skip automated test for now as it requires mocking Frigate snapshots)

**Step 3: Commit**

```bash
git add factory_analytics/services.py
git commit -m "refactor(services): clarify snapshot failures in vision test"
```

---

### Task 4: Update Settings UI

**Files:**
- Modify: `factory_analytics/templates/settings.html`

**Step 1: Add new buttons and status areas**

Replace the existing `Test Connection` block with:
- `Check API & Model` button + result span.
- `Run Vision Test` button + result span.

**Step 2: Wire up JavaScript handlers**

Add handlers for `btnTestApi` and update `btnTestVision` (which is `testOllamaBtn`).

**Step 3: Commit**

```bash
git add factory_analytics/templates/settings.html
git commit -m "feat(ui): split ollama health checks into API and Vision buttons"
```

---

### Task 5: Final End-to-End Verification

**Step 1: Run all tests**

Run: `pytest -q`
Expected: PASS

**Step 2: Manual smoke test on Settings page**

**Step 3: Update features.md and implementation docs**

**Step 4: Commit**

```bash
git add docs/features.md docs/implementation/2026-03-31-split-ollama-health-checks.md
git commit -m "docs: finalize split ollama health checks documentation"
```
