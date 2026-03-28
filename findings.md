# Findings

## 2026-03-28
- `factory_analytics/integrations/frigate.py` currently fetches Frigate images with `h=720&quality=70`, which downscales LLM input at capture time.
- `factory_analytics/services.py` sends `_capture_snapshot()` output directly into `OllamaClient.classify_image()`, so low-resolution capture affects all camera/group analysis.
- UI already constrains evidence preview size with CSS in `factory_analytics/static/app.js`; this can remain a presentation-only concern.
- `factory-analytics.sh debug` runs `start_debug_all()`, which backgrounds both uvicorn processes and tails logs.
- Repo uses Python with `requirements.txt`, FastAPI app in `factory_analytics`, and pytest in `tests/`.
- Running `./factory-analytics.sh debug` while services are already running reproduces `[Errno 48] Address already in use` in both API and MCP logs.
- `factory_analytics/main.py` no longer contains the old `__PLACEHOLDER__`; the current `/api/logs/tail` implementation is valid, so that earlier log noise is stale.
- The current debug run also reveals a real worker failure: `RuntimeError: Model qwen3.5:9b returned invalid label: person`.
- `requirements.txt` already includes `Pillow==10.4.0`, so the historical `ModuleNotFoundError: No module named 'PIL'` in logs is stale and not the current root cause.
