# AGENTS.md

This repository uses `docs/` as the persistent memory layer for all agent sessions.

The goal of this file is to make work resumable, auditable, language-agnostic, and safe across broken sessions, model changes, and tool changes.

---

## Core rule

For every meaningful code or config change:

1. create or update an implementation note under `docs/implementation/`
2. update the actual affected project files when the task requires it
3. update `docs/todos.md`
4. update `docs/features.md` when a feature is created, changed, released, or removed
5. Dtabase sqlite data/db/factory_analytics.db
6. read env always .env & .env.example
7. Main application files here factory_analytics*
8. application starts via factory-analytics.sh cmd 
9. Logs here logs*
No task is considered complete until both the real project files and the docs memory are updated.


---

## Canonical memory files

Use these files as the single source of truth for project continuity:

- `AGENTS.md` -> repository-wide operating rules for agents
- `docs/todos.md` -> current work queue, status, blockers, next steps, resume point
- `docs/features.md` -> implemented features and their current state
- `docs/implementation/YYYY-MM-DD-short-topic.md` -> detailed change log for each task/change

If the repository already contains `docs/implentation/` with the misspelling, either:

- rename it once to `docs/implementation/`, then use only the corrected path, or
- keep the old path for backward compatibility, but use one spelling consistently everywhere

Preferred canonical path: `docs/implementation/`.

---

## Required directory structure

```text
/
├─ AGENTS.md
├─ docs/
│  ├─ todos.md
│  ├─ features.md
│  └─ implementation/
│     ├─ 2026-03-28-bootstrap-project-memory.md
│     └─ 2026-03-28-auth-session-hardening.md
└─ ...project files...
```

If `docs/` does not exist, create it before starting work.
If `todos.md` or `features.md` does not exist, create them before making code changes.
If `implementation/` does not exist, create it before the first task note.

---

## Session start protocol

At the beginning of every session, in this exact order:

1. read `AGENTS.md`
2. read `docs/todos.md`
3. read `docs/features.md`
4. read the newest relevant file(s) under `docs/implementation/`
5. determine:
   - what is in progress
   - what is blocked
   - what was last changed
   - what must be resumed next

If the prior session was interrupted, resume from `docs/todos.md` first.
If `docs/todos.md` conflicts with an implementation note, trust the newest implementation note and then repair `docs/todos.md`.

---

## Session end protocol

Before ending a task or handing work back:

1. update the relevant implementation note
2. mark task status in `docs/todos.md`
3. update `docs/features.md` if behavior, capability, or status changed
4. record remaining blockers, risks, and next actions
5. ensure another agent can resume without needing hidden context

Never end a session with undocumented partial work.

---

## Change workflow

For each task, follow this flow:

### 1) Understand
- inspect the repository structure
- detect the language(s), framework(s), package manager(s), test runner(s), and deployment style
- do not assume the stack

### 2) Create memory first
Create or update an implementation note before or immediately when starting meaningful work.

Naming format:

```text
docs/implementation/YYYY-MM-DD-short-topic.md
```

Examples:

```text
docs/implementation/2026-03-28-payment-webhook-retry.md
docs/implementation/2026-03-28-flutter-login-validation.md
docs/implementation/2026-03-28-go-cache-invalidation.md
```

### 3) Execute safely
- make the smallest correct change
- update every affected source file, config file, test file, asset, script, schema, or docs file required by the task
- do not stop at planning or memory updates if the requested work also requires real file changes
- preserve existing style and architecture unless the task requires otherwise
- avoid unrelated edits
- avoid silent breaking changes
- if a migration or contract change is required, document impact clearly

### 4) Verify
Run the narrowest reliable checks for the affected area.
Examples include linting, type checks, unit tests, integration tests, build checks, or app-specific validation.

### 5) Write back memory
Update all three memory layers:
- implementation note
- todos
- features

---

## Global language-agnostic rules

This file must work across all languages and stacks.
Always detect the stack from repository files before acting.

Common signals:

- Node.js / TypeScript / JavaScript: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `tsconfig.json`
- Python: `pyproject.toml`, `requirements.txt`, `poetry.lock`, `uv.lock`, `Pipfile`
- Go: `go.mod`
- Rust: `Cargo.toml`
- Java / Kotlin: `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle`
- PHP: `composer.json`
- Ruby: `Gemfile`
- .NET: `*.csproj`, `*.sln`
- Flutter / Dart: `pubspec.yaml`
- Elixir: `mix.exs`
- C/C++: `CMakeLists.txt`, `Makefile`, `meson.build`
- Dockerized repos: `Dockerfile`, `docker-compose.yml`, `compose.yml`

Rules:

- use the package manager already used by the repo
- use the formatting and linting tools already configured by the repo
- use the test strategy already used by the repo
- do not introduce new tooling unless required and documented
- do not rewrite working build systems without explicit need

---

## `docs/todos.md` contract

`docs/todos.md` is the resume engine for broken sessions.
It should stay concise, current, and execution-focused.

Recommended structure:

```md
# TODOs

## In Progress
- [ ] Fix session expiry handling in API middleware
  - Owner: agent
  - Started: 2026-03-28
  - Related: docs/implementation/2026-03-28-auth-session-hardening.md
  - Next step: update refresh-token rotation tests

## Planned
- [ ] Add admin audit export endpoint

## Blocked
- [ ] Finish S3 upload retry flow
  - Blocker: waiting for bucket policy confirmation

## Done
- [x] Add login rate limiting
  - Done: 2026-03-28
  - Related: docs/implementation/2026-03-28-auth-session-hardening.md
```

Rules:

- move items between `Planned`, `In Progress`, `Blocked`, and `Done`
- every in-progress task must include a next step
- every meaningful task should link to its implementation note
- when a session breaks, resume from the first `In Progress` item unless a newer implementation note says otherwise
- remove ambiguity; write tasks so another agent can continue immediately

---

## `docs/features.md` contract

`docs/features.md` is the stable index of what exists in the product.
It is not a task log.
It is the capability map.

Recommended structure:

```md
# Features

## Authentication
- Feature: Session-based login
  - Status: active
  - Paths: `src/auth/*`, `api/auth/*`
  - Notes: refresh rotation enabled; lockout after repeated failures
  - Last updated: 2026-03-28

## Billing
- Feature: Webhook retry handling
  - Status: partial
  - Paths: `services/billing/webhooks/*`
  - Notes: retry queue implemented, dead-letter dashboard pending
  - Last updated: 2026-03-28
```

Rules:

- update when behavior changes, not for every tiny refactor
- include current status such as `planned`, `partial`, `active`, `deprecated`, `removed`
- include the main code paths where the feature lives
- include short notes that help future agents understand the current reality

---

## Implementation note template

Use this template for every file in `docs/implementation/`:

```md
# YYYY-MM-DD - Topic

## Summary
One short paragraph describing the goal.

## Why
- Business reason
- Bug reason
- Reliability/security/performance reason

## Scope
- What is included
- What is intentionally not included

## Changed files
- `path/to/file.ext` - what changed
- `path/to/file.ext` - what changed

## Decisions
- Decision made
- Alternative considered
- Why this approach was chosen

## Verification
- Commands run
- Tests added/updated
- Manual verification performed

## Risks / Follow-ups
- Known limitation
- Next recommended step
- Dependency or blocker

## Resume point
- Exact next action if work is not finished
```

Rules:

- keep it short but complete
- prefer append/update over creating duplicate notes for the same task on the same date
- if scope changes significantly, note that explicitly
- if a task spans multiple days, keep updating the same file until the topic naturally splits

---

## How to handle broken sessions

If context is lost or the session is restarted:

1. read `AGENTS.md`
2. read `docs/todos.md`
3. open the implementation note linked from the first `In Progress` task
4. inspect the changed files listed there
5. continue from the `Resume point`
6. after resuming, refresh all three memory files before finishing

Do not restart from scratch if memory files already contain the latest state.

---

## How to add a new task

When starting a new task:

1. add it to `docs/todos.md`
2. create or update a matching implementation file
3. begin work
4. when the feature materially changes, update `docs/features.md`

---

## How to close a task

A task is only closed when all are true:

- code/config changes are complete
- affected checks were run as appropriate
- `docs/implementation/...` is updated
- `docs/todos.md` is updated
- `docs/features.md` is updated if capability changed
- a future agent can resume or maintain it without hidden context

---

## Documentation style rules

- prefer short sections and bullets over long prose
- prefer exact file paths
- prefer exact dates in `YYYY-MM-DD`
- prefer explicit status words: `planned`, `in progress`, `blocked`, `partial`, `active`, `deprecated`, `removed`, `done`
- write facts, not guesses
- if something is uncertain, mark it clearly as uncertain

---

## Safety rules for agents

- do not delete or overwrite docs memory files without reason
- do not mark work done if verification is missing
- do not hide unfinished work
- do not claim a feature exists unless `docs/features.md` reflects it
- do not leave `In Progress` tasks without a clear next step
- do not create duplicate TODO entries for the same active task

---

## Recommended minimum startup behavior for any agent

On every run, agents should do the following before major edits:

1. read `AGENTS.md`
2. synchronize understanding from `docs/todos.md` and `docs/features.md`
3. open the latest relevant implementation note
4. detect stack and commands from the repo itself
5. make the change
6. verify appropriately
7. write back to memory docs

---

## Optional starter files

If missing, initialize these:

### `docs/todos.md`

```md
# TODOs

## In Progress

## Planned

## Blocked

## Done
```

### `docs/features.md`

```md
# Features
```

---

## File update rule

If a task requires changes in existing files, make those changes too.
Do not only update `docs/` and leave the real implementation undone.
Always keep implementation notes in sync with the exact files that were created, modified, renamed, or removed.

## Final instruction

The repository memory must survive model changes, agent changes, IDE changes, and broken sessions.
Treat `docs/` as durable project memory.
Treat `AGENTS.md` as the operating system for that memory.