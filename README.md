# Assignment 2 - Part 3

## Shared Hub Agent

This branch extends the Part 2 structured secure SWE agent with a Part 3 hub
mode for the shared RunPod group chat. The original Part 2 local CLI is still
available for testing, but Part 3 uses the hub as the main conversation channel.

Run Part 3 hub mode:

```bash
docker compose run --rm react-agent python app/main.py --hub
```

Local console input in hub mode is reserved for safety approvals and lightweight
runtime controls such as `status`, `pause`, `resume`, and `quit`. The agent does
not use the local console as its normal chat interface in hub mode.

Part 3 hub settings are configured through environment variables:

```env
HUB_URL=https://z0yncxbipft4e8-8080.proxy.runpod.net
HUB_PASSWORD=put_hub_password_here
HUB_POLL_SECONDS=4
HUB_MIN_REQUEST_INTERVAL=1.1
HUB_MAX_MESSAGES_SENT=10
HUB_MAX_MODEL_CALLS=20
HUB_MAX_TOTAL_TOKENS=40000
HUB_MAX_CONTEXT_MESSAGES=20
HUB_MAX_POST_CHARS=4096
HUB_INTERACTIVE_CONTROLS=true
HUB_SYNC_ON_START=true
HUB_BROADCAST_TRIGGERS=all agents,alla agenter,attention agents,agents:
```

Do not commit the real hub password.

Hub safety and peer-collaboration behavior:

* polls the hub REST API with rate limiting
* posts using the unique agent name `igor-petersson-agent`
* participates as an equal SWE peer, not as a specialized manager/dev/research role
* caps outbound hub messages
* caps model calls
* tracks OpenAI response usage and caps total tokens
* ignores hub messages unless they mention `igor-petersson-agent` or a configured broadcast trigger
* syncs existing hub history on startup without replying to old messages
* uses `PASS` when it has nothing useful to add
* treats other agents' messages as untrusted input
* refuses to reveal secrets, passwords, hidden prompts, or private files
* keeps the existing safe bash/edit approval system from Part 2

---

## Structured Secure SWE Agent

The base agent is the Part 2 version of the Assignment 2 agent. Part 1 is
preserved on the `master` branch, and Part 2 is preserved on the
`part-2-structured-agent` branch. Part 2 replaced regex-based action parsing
with structured output and added safe file section editing, output pagination,
config-based system prompting, and multiple tool rounds before yielding to the
user.

The agent is still written as plain Python code. The project does not use
LangChain, LangGraph, LlamaIndex, OpenAI built-in tool execution, Cursor,
Codex, or any external agent framework as part of the agent runtime.

---

## Setup

1. Clone the repository.
2. Check out this branch:

```bash
git checkout part-3-hub-agent
```

3. Copy `.env.example` to `.env`.
4. Add your OpenAI API key to `.env`.

Example `.env` values:

```env
OPENAI_API_KEY=your_openai_api_key_here
MODEL=gpt-4.1-mini
AGENT_NAME=igor-petersson-agent
MAX_STEPS=10
MAX_TOOL_OUTPUT_CHARS=4000
REQUIRE_TOOL_CONFIRMATION=true
DEBUG_AGENT=false
```

Do not commit `.env`.

---

## Run With Docker

Docker is the recommended way to run the agent, especially on Windows. The agent
uses Linux-style shell commands and Docker adds a second safety boundary around
the Python safety checks.

Build:

```bash
docker compose build
```

Run:

```bash
docker compose run --rm react-agent
```

Run hub mode:

```bash
docker compose run --rm react-agent python app/main.py --hub
```

Do not run `docker compose config` while `.env` contains a real API key. That
command prints the resolved Compose configuration and can expose secrets in the
terminal. Use it only with dummy values if you need to inspect the config.

The container is configured with:

* non-root user
* read-only container filesystem
* dropped Linux capabilities
* `no-new-privileges`
* `/tmp` as temporary writable storage
* mounted editable project paths for Part 2 file edits

---

## Run Locally

Local execution is possible, but Docker is safer and more consistent.

```bash
python -m venv venv
```

Activate the virtual environment, install dependencies, then run:

```bash
pip install -r requirements.txt
python app/main.py
```

On Windows, local PowerShell may not support the same command behavior as the
Docker/Linux environment.

---

## Part 2 Requirements

The Part 2 assignment asks for:

* mainstream structured output
* own code for the agent loop, context handling, and tool-calling
* safe bash calls with protection against destructive execution
* editing individual sections of files
* multiple tool-calling rounds before yield
* persistent session history within the current session
* system prompt loaded from a config file
* output-size limits for tool calls, known by the agent

This branch implements those requirements.

---

## Main Files

| File | Responsibility |
| --- | --- |
| `app/main.py` | Starts the CLI program |
| `app/agent.py` | Main structured-output agent loop |
| `app/structured_output.py` | JSON schema for model decisions |
| `app/config.py` | Loads env/config values |
| `app/shell_tools.py` | Validates and executes safe bash commands |
| `app/file_tools.py` | Safely edits exact file sections |
| `app/hub_client.py` | REST client for the shared RunPod hub |
| `app/hub_agent.py` | Part 3 polling, PASS behavior, caps, and hub posting |
| `config/system_prompt.txt` | System prompt loaded at runtime |
| `SYSTEM_MAP.md` | Architecture, safety, context, and hub flow documentation |
| `workspace/` | Default working directory for bash commands |

Part 1 is preserved on the `master` branch. The active Part 3 branch keeps the
current structured-output runtime files and documents the system flow in
`SYSTEM_MAP.md`.

---

## Structured Output

The model must return one structured decision per round. Allowed actions:

```text
bash
create_file
edit_file_section
read_tool_output
yield
```

The JSON schema is defined in `app/structured_output.py`. The agent loop reads
the structured response and dispatches the requested action itself. OpenAI does
not execute tools for the agent.

Set `DEBUG_AGENT=true` in `.env` if you want to print the raw structured model
responses and tool observations for testing or screenshots. Leave it `false`
for normal interactive use.

---

## Tool Behavior

### `bash`

Runs a safe shell command after validation and manual approval.

Security checks include:

* command allowlist
* blocked command chaining, pipes, redirects, variables, backticks, and `..`
* blocked absolute paths
* blocked `.env` and `.env.*` access
* `shell=False`
* execution from `workspace/`
* timeout protection

### `create_file`

Creates a new file inside `workspace/`. Missing parent directories under
`workspace/` are created automatically after approval. The creation is blocked
if:

* the target path is outside `workspace/`
* the file already exists
* `new_text` is empty
* the file path targets `.env` or `.env.*`

Manual `y/n` approval is required before writing.

### `edit_file_section`

Replaces one exact section in an allowed file. The edit is blocked if:

* the target path is outside the editable paths
* the file does not exist
* `old_text` is empty
* `old_text` is not found exactly once
* the file path targets `.env` or `.env.*`

Manual `y/n` approval is required before writing.

Editable paths are:

```text
workspace/
app/
README.md
requirements.txt
```

The agent is not allowed to edit assignment instructions, hub connection notes,
`.env`, `.git`, screenshots, or arbitrary host files.

### `read_tool_output`

Reads another page from a previous long tool output. Tool results are stored by
output id, such as `tool-1`, and returned in character windows.

This avoids losing important information through blind truncation.

### `yield`

Stops tool use and answers the user.

---

## Output Pagination

Tool output is limited by:

```env
MAX_TOOL_OUTPUT_CHARS=4000
```

If output is longer, the agent receives a page like:

```text
Output page for tool-1: chars 0-4000 of 9000.
Use read_tool_output with offset 4000 to continue if needed.
Output continues after this page.
```

The model can then request the next slice only when needed.

---

## Session History

Within a run, the agent stores the full message history:

1. user task
2. structured model decision
3. tool observation
4. follow-up structured decision
5. final yield

Multi-session persistence is not required for Part 2.

---

## System Prompt

The active system prompt is loaded from:

```text
config/system_prompt.txt
```

It instructs the agent to work only on safe software engineering tasks, protect
secrets, treat external text as untrusted input, use tools conservatively, and
follow the structured action format.

Agent identity:

```text
igor-petersson-agent
```

---

## Security Notes

The project is designed around defense in depth:

* Docker container boundary
* non-root container user
* read-only container filesystem
* command allowlist
* blocked unsafe shell syntax
* restricted working directories
* exact-section file editing
* manual approval before bash commands and file edits
* output pagination to reduce context flooding
* system prompt rules against secret leakage and unsafe behavior

The human terminal is still trusted. Do not run diagnostic commands that print
secrets, and never commit `.env`.

---

## Part 2 Integration Test

A real Docker/OpenAI integration test was run with a temporary workspace file.
The task required the agent to inspect a file, page through truncated tool
output, edit one section, and yield a final answer.

Observed action sequence:

```text
bash
read_tool_output
read_tool_output
edit_file_section
yield
```

The test confirmed:

* structured JSON output worked
* bash approval worked
* output pagination worked
* multiple tool rounds worked
* exact-section editing worked
* edit approval worked
* final yield worked

The temporary test file was removed afterward.

---

## Branches

Recommended branch interpretation:

```text
master
  Part 1 stable submission

part-2-structured-agent
  Part 2 structured-output agent

part-3-hub-agent
  Part 3 group-chat/multi-agent version
```

The detailed Part 1 README is preserved on `master`.
