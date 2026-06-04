# Assignment 2 VG — Igor Petersson Agent

A Claude Code / Codex competitor built from scratch in Python. Parallel sub-agents,
real-time cost control, browser GUI, and a layered safety system — no external agent
frameworks used.

---

## Quick Start

1. Clone the repository.
2. Check out this branch:

```bash
git checkout vg-engineering-agent
```

3. Copy `.env.example` to `.env` and add your OpenAI API key.
4. Build the Docker image:

```bash
docker compose build
```

5. Start the browser GUI:

```bash
python gui/server.py
```

The browser opens automatically at `http://localhost:8765`.

---

## GUI

The browser GUI is the main interface for this submission. It provides:

- **Run** — send a task to the agent and watch it stream live output with real-time cost tracking
- **Tests** — run the full VG requirements test suite inside Docker with one click
- **Logs** — browse the last 50 agent sessions
- **Config** — inspect all configuration values (API keys are masked)

The GUI spawns Docker containers on demand. Docker Desktop must be running.

---

## VG Features

### VG.1 — Parallel sub-agents

The main agent can spawn up to 3 read-only sub-agents in parallel using `ThreadPoolExecutor`:

```text
debug-agent   — finds bugs, failure modes, and suspicious logic
test-agent    — suggests test cases and edge cases
verify-agent  — checks whether the work meets requirements
```

Sub-agents receive bounded recent evidence from the main agent's observations.
Their structured results are fed back into the main agent as a normal observation.
Sub-agents cannot edit files, run bash, spawn other agents, or post to the hub.

### VG.2 — Advanced context engineering

- Conversation history is trimmed to `MAX_CONTEXT_MESSAGES` before each model call.
  The system prompt and a compact notice are always preserved.
- Tool output is paginated to `MAX_TOOL_OUTPUT_CHARS` per page.
- Evidence passed to sub-agents is capped at `SUBAGENT_EVIDENCE_CHARS`.
- No LangChain, LangGraph, CrewAI, AutoGen, or any other agent framework.

### VG.3 — Real-time cost monitoring, budget warning, hard cap

- Token count and estimated USD cost are printed after every step.
- A budget warning is injected into the agent's context at `TOKEN_WARNING_RATIO` (default 80%).
- A hard cap at `MAX_TOTAL_TOKENS` stops the agent before AND after each model call.

### VG.4 — Protection against harmful tool calls

Bash commands are validated before execution:

- command allowlist (ls, cat, head, tail, grep, find, sed, python, pytest)
- blocked: rm, mv, cp, chmod, curl, wget, ssh, and others
- blocked: `&&`, `|`, `;`, backticks, `$`, `>`, `<`
- blocked: absolute paths
- blocked: `.env` and `.env.*` access
- blocked: `find -delete`, `sed -i`, and other destructive options

### VG.5 — Bash execution

The agent runs real shell commands via `execute_bash`. Commands run inside the
Docker container with `workspace/` as the working directory.

### VG.6 — Partial file editing

`edit_file_section` replaces one exact section of a file (find-and-replace a region),
not a whole-file overwrite. The edit is blocked if the target is outside editable paths
or targets `.env`.

### VG.7 — Deployable packaging

Docker Compose with a documented setup path. The browser GUI opens automatically.

### VG.8 — Config file and env-var secrets

All configuration lives in `config.py` and is loaded from environment variables.
Secrets come from `.env` (git-ignored). No API key is hardcoded anywhere in the source.

### VG.9 — Agent autonomy: tool-call vs yield

The model decides each turn whether to call a tool or yield back to the user.
The framework never forces a stop — only the model's `yield` action or the hard
token cap ends a session.

---

## Running Without the GUI

Run the agent interactively from the command line:

```bash
docker compose run --rm react-agent
```

Run the VG test suite directly:

```bash
docker compose run --rm \
  -v $(pwd)/test_vg_requirements.py:/agent/test_vg_requirements.py \
  react-agent python test_vg_requirements.py
```

Run hub mode (Part 3 group chat):

```bash
docker compose run --rm react-agent python app/main.py --hub
```

---

## Project Structure

| Path | Description |
|---|---|
| `app/main.py` | Entry point — CLI or hub mode |
| `app/agent.py` | Main agent loop, context trimming, cost tracking |
| `app/subagents.py` | Parallel sub-agent runner (ThreadPoolExecutor) |
| `app/structured_output.py` | JSON schema for model decisions |
| `app/shell_tools.py` | Bash validation and execution |
| `app/file_tools.py` | Partial file editing |
| `app/tracing.py` | Runtime trace output |
| `app/hub_agent.py` | Hub polling and peer-agent behavior |
| `app/hub_client.py` | REST client for the shared RunPod hub |
| `app/config.py` | All configuration loaded from env vars |
| `config/system_prompt.txt` | System prompt loaded at runtime |
| `gui/server.py` | Browser GUI backend (localhost:8765) |
| `gui/index.html` | Browser GUI frontend |
| `workspace/` | Working directory for bash and file edits |

---

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```env
OPENAI_API_KEY=your_openai_api_key_here
MODEL=gpt-4.1-mini
AGENT_NAME=igor-petersson-agent

# Agent limits
MAX_STEPS=10
MAX_TOTAL_TOKENS=200000
TOKEN_WARNING_RATIO=0.8
ESTIMATED_COST_PER_1K_TOKENS=0.0010
MAX_CONTEXT_MESSAGES=40
MAX_TOOL_OUTPUT_CHARS=4000
MAX_SUBAGENTS=3
SUBAGENT_TIMEOUT_SECONDS=60
SUBAGENT_EVIDENCE_CHARS=6000

# Debugging
DEBUG_RUNTIME_TRACING=false
DEBUG_AGENT=false
```

Set `DEBUG_RUNTIME_TRACING=true` to see tagged trace lines for every loop step,
tool dispatch, sub-agent call, context trim, and budget event.

Do not commit `.env`.

---

## Branches

| Branch | Description |
|---|---|
| `master` | Part 1 — basic agent |
| `part-2-structured-agent` | Part 2 — structured output, safe bash, file editing |
| `part-3-hub-agent` | Part 3 — shared group-chat hub agent |
| `vg-engineering-agent` | VG — this branch, Claude Code competitor with GUI and sub-agents |
