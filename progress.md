# Progress

## 2026-03-28
- Read `AGENTS.md`, `docs/todos.md`, `docs/features.md`, `.env`, and `.env.example`.
- Reviewed current implementation notes related to camera management and service script behavior.
- Confirmed approved design direction: keep UI thumbnails small, but use full-resolution snapshots for saved evidence and LLM input.
- Reproduced `./factory-analytics.sh debug` against a running instance; confirmed current startup collision (`[Errno 48] Address already in use`) and a real worker failure where Ollama returns `label: person`.
- Confirmed `/api/logs/tail` code is currently valid; old placeholder stack traces in logs are historical noise rather than the active code state.
- Verified the true full-resolution source is go2rtc `:1984/api/frame.jpeg?src=<camera>`; Frigate `latest.jpg` is only `320x320` for these cameras.
- Added and passed regression tests for full-resolution capture, debug port preflight, and scheduler deduplication.
- Confirmed a fresh app-path snapshot now saves at `1920x1080`.
- Confirmed clean `debug` startup after stopping services; current remaining worker noise comes from historical queued jobs and honest Ollama upstream failures rather than the launcher itself.
- Updated `/history` so evidence renders as a larger inline photo preview instead of a plain `view` link, with click-through to the original full image.
- Added group-run behavior so grouped cameras are included regardless of standalone enabled state, and partial merges continue with available cameras while recording missing camera names in notes.
- Added UI hooks in History and Processed Events for LLM notes and merge metadata display.
- Extended group runs to create durable group job/segment history records so merged analysis results can be read back from stored history data.
- Updated History and Processed views to show explicit Group Result badge/name for persisted merged group records.
- Added Control Center and API Explorer pages with read-only config inspection, skill inventory, platform install guidance, and route catalog metadata endpoints.
