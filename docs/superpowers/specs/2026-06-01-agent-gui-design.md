# Agent GUI — Design Spec

**Date:** 2026-06-01  
**Project:** Igor Petersson Agent (VG Assignment)  
**Branch:** vg-engineering-agent

---

## Overview

A browser-based dashboard for the VG engineering agent. Lets the user run tasks, watch live agent output, execute VG requirement tests, and inspect configuration — all without touching the terminal.

---

## Aesthetic

- **Background:** `#0f1117` (dark slate)
- **Glass panels:** `rgba(255,255,255,0.03)` background + `rgba(255,255,255,0.07)` border + `backdrop-filter: blur(8px)`
- **Colored left borders** on each panel (semantic color-coding):
  - Violet `#a78bfa` → agent network, sub-agents
  - Blue `#60a5fa` → task input
  - Green `#22c55e` → output log, safety allowed
  - Amber `#f59e0b` → token budget
  - Red `#ef4444` → blocked/error
- **Font:** Fira Code (Google Fonts)
- **Accent text:** violet `#a78bfa` for primary, amber `#f59e0b` for cost/warnings
- **Status colors:** green = idle/ok, amber = running/warn, red = blocked/error

---

## Files

```
gui/
  index.html    — full frontend (HTML + CSS + JS, single file)
  server.py     — Python stdlib HTTP server, no new dependencies
```

`.gitignore` already excludes sensitive files. `gui/` is safe to commit.

---

## Starting the GUI

```powershell
python gui/server.py
# Opens http://localhost:7680 automatically
```

No pip installs, no Docker changes needed.

---

## Architecture

### Backend — `gui/server.py`

Minimal `http.server.BaseHTTPRequestHandler`. Three endpoints:

| Method | Path | Action |
|--------|------|--------|
| GET | `/` | Serves `gui/index.html` |
| GET | `/api/run-tests` | Runs all tests via Docker, streams stdout line by line |
| GET | `/api/run-tests?class=TestVG1_...` | Runs one test class, streams stdout |
| POST | `/api/run-agent` | Runs agent in Docker with provided task, streams stdout |
| GET | `/api/logs` | Returns saved log history as JSON |

Streaming uses HTTP chunked transfer encoding. Frontend reads with `fetch()` + `ReadableStream` — no WebSocket, no polling.

**Docker commands the server runs:**

```bash
# Tests
docker compose run --rm \
  -v ./test_vg_requirements.py:/agent/test_vg_requirements.py \
  react-agent python test_vg_requirements.py [ClassName]

# Agent
docker compose run --rm \
  -e DEBUG_RUNTIME_TRACING=true \
  -e ESTIMATED_COST_PER_1K_TOKENS=0.0010 \
  react-agent
# Task piped to stdin
```

Logs are appended to `gui/session_logs.json` by the server (one entry per run, capped at 50 entries).

### Frontend — `gui/index.html`

Single-file app. Layout:

```
┌─────────────────────────────────────────────────────────┐
│ HEADER: name | status dot | model | Docker ✓ | $cost    │
├────┬─────────────────────────────────┬───────────────────┤
│    │                                 │                   │
│ N  │  MAIN CONTENT (active view)     │  RIGHT SIDEBAR    │
│ A  │                                 │  Token budget bar │
│ V  │                                 │  Sub-agent status │
│    │                                 │  Safety counters  │
│    │                                 │  Session info     │
└────┴─────────────────────────────────┴───────────────────┘
```

**Left nav** (56px wide): icon buttons for each view.  
**Right sidebar** (260px): always visible stats — token budget, sub-agent status, safety counters.  
**Main area**: switches between the 4 views below.

---

## Views

### 1. Run

- **Agent network SVG** — main-agent node at top, three sub-agent nodes below, animated dashed connection lines. Nodes pulse/glow when running.
- **Task input** — textarea + `▶ Run Task` button + `⌫ Clear`. Ctrl+Enter to submit.
- **Demo buttons** — 3 one-click scenarios from `VG_DEMO_HANDOFF.md`:
  - "Inspect calculator.py"
  - "Parallel sub-agents (hangman)"
  - "Hard cap demo (MAX_TOTAL_TOKENS=1)"
- **Live output log** — colorized by action type (bash=blue, agents=violet, yield=green, warn=amber, block=red). Scrolls automatically. Shows `Usage status:` lines inline.

### 2. Tests

- **Test list** — one row per VG requirement class (VG.1–VG.9). Each row shows: label, name, test count, status badge, `▶` run button.
- **Run All button** — runs complete test suite, updates all rows live.
- **Output pane** — streams raw test output below the list. Lines color-coded: `ok`=green, `FAIL`=red, `skipped`=amber.
- Status badges: `—` (not run) → `running…` (animated) → `N/N ✓` (passed) or `N fail` (failed).

### 3. Logs

- **Session list** — each past run as a collapsible row: timestamp, task summary, duration, token count.
- **Detail view** — click a session to expand full output.
- **Clear button** — wipes `gui/session_logs.json`.
- Capped at 50 sessions.

### 4. Config

- Read-only display of all settings, grouped by category (Model, Limits, Context, Safety, Sub-agents, Cost).
- Secrets shown as `sk-...••••••` (first 3 chars + masked).
- Values sourced from the server reading `.env` at startup (passed as JSON to frontend).

---

## Right Sidebar (always visible)

| Section | Contents |
|---------|----------|
| Token Budget | Progress bar (green→amber→red), tokens used/max, estimated cost, model calls |
| Sub-agents | debug / test / verify — each with status badge (idle/running/done/blocked) |
| Safety | Blocked count (red), Allowed count (green), confirmation mode on/off |
| Session | Current step, last action, status |

Budget warning banner appears inline when `>80%` used.

---

## Data Flow

```
User types task
  → POST /api/run-agent
    → server: docker compose run (stdin=task)
      → Docker agent streams stdout
        → server: chunked HTTP response
          → frontend: ReadableStream, parse lines
            → update log, update sidebar stats, update agent network SVG
```

Tests follow the same pattern with GET instead of POST.

---

## Error Handling

- If Docker is not running: server returns a clear error message; frontend shows it in the log as a `block` line.
- If a test class is not found: Docker returns a non-zero exit code; frontend shows partial output + error.
- If the server is not running: frontend catches `fetch()` failure and shows "Start gui/server.py to connect".
- Agent stop button: sends `AbortController.abort()` to cancel the fetch; server detects broken pipe and kills the subprocess.

---

## Out of Scope

- Authentication / multi-user
- Real-time cost from OpenAI billing API (estimated cost only)
- Editing config from the GUI
- Mobile layout

---

## Success Criteria

1. `python gui/server.py` starts the server and opens the browser with no errors.
2. Typing a task and clicking Run streams live output from the Docker agent.
3. Clicking "Run All" on the Tests view runs all 49 tests and shows pass/fail per class.
4. Demo buttons trigger the correct pre-set tasks.
5. Config view shows all settings with secrets masked.
6. Logs view shows previous runs and their output.
7. Sidebar stats (tokens, cost, sub-agent status) update in real time during a run.
