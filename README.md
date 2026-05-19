# Assignment 2 - Part 2

## Structured Secure SWE Agent

This branch contains the Part 2 version of the Assignment 2 agent. Part 1 is
preserved on the `master` branch. Part 2 builds on that foundation by replacing
regex-based action parsing with structured output and by adding safe file
section editing, output pagination, config-based system prompting, and multiple
tool rounds before yielding to the user.

The agent is still written as plain Python code. The project does not use
LangChain, LangGraph, LlamaIndex, OpenAI built-in tool execution, Cursor,
Codex, or any external agent framework as part of the agent runtime.

---

## Setup

1. Clone the repository.
2. Check out this branch:

```bash
git checkout part-2-structured-agent
```

3. Copy `.env.example` to `.env`.
4. Add your OpenAI API key to `.env`.

Example `.env` values:

```env
OPENAI_API_KEY=your_openai_api_key_here
MODEL=gpt-4.1-mini
AGENT_NAME=igorpetersson-codeagent
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
| `config/system_prompt.txt` | System prompt loaded at runtime |
| `workspace/` | Default working directory for bash commands |

Legacy Part 1 files such as `parser.py` and `prompts.py` remain in the repo for
history, but the active Part 2 loop uses `structured_output.py` and
`config/system_prompt.txt`.

---

## Structured Output

The model must return one structured decision per round. Allowed actions:

```text
bash
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
igorpetersson-codeagent
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
  Future Part 3 group-chat/multi-agent version
```

The detailed Part 1 README is preserved on `master`.
