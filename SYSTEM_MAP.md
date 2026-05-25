# Assignment 2 System Map

This document explains how the current Part 3 branch is structured. It is meant
as a code-review and VG preparation map for the Python-based agent system.

## Runtime Modes

The entrypoint is `app/main.py`.

```text
python app/main.py
```

Starts the local Part 2 CLI. The user types tasks in the local console, and the
same `AgentSession` stays alive across prompts until `exit` or `quit`.

```text
python app/main.py --hub
```

Starts the Part 3 hub agent. Normal conversation happens through the shared
RunPod hub. The local console is only used for tool approvals and live controls
such as `status`, `pause`, `resume`, and budget changes.

## High-Level Architecture

```text
main.py
  |
  +-- local mode ----------------+
  |                              |
  v                              |
AgentSession <-------------------+
  |
  +-- model_decision()
  |     OpenAI chat completion with JSON schema response_format
  |
  +-- observation_for()
        |
        +-- bash -> shell_tools.execute_bash()
        +-- edit_file_section -> file_tools.edit_file_section()
        +-- read_tool_output -> AgentSession output store
        +-- spawn_subagents -> subagents.run_subagents()
        +-- verify -> verify-agent read-only pass
        +-- yield -> final answer

main.py --hub
  |
  v
HubAgent
  |
  +-- HubClient.fetch_messages()
  +-- filter by own name / broadcast triggers
  +-- AgentSession.run_task()
  +-- HubClient.post_message()
```

## Agent Loop

The main loop lives in `app/agent.py` inside `AgentSession.run_task()`.

1. The session starts with `config/system_prompt.txt`.
2. The configured `AGENT_NAME` is added as session context.
3. A user task is appended to `self.messages`.
4. `model_decision()` calls the OpenAI API with the configured model.
5. The model must return one structured JSON decision.
6. The decision is appended to history.
7. If the action is `yield`, the answer is returned.
8. Otherwise `observation_for()` dispatches the requested tool.
9. The tool observation is appended back into history.
10. The loop continues until `yield` or `MAX_STEPS`.

The loop is owned by local Python code. The model does not execute tools itself.

## Structured Output

The JSON schema is defined in `app/structured_output.py`.

Allowed actions:

```text
bash
edit_file_section
read_tool_output
spawn_subagents
verify
yield
```

All fields are required by the schema. Unused fields are filled with an empty
string, `0`, or an empty list. This keeps parsing simple and predictable.

## Tool Dispatch

Tool dispatch happens in `observation_for()` in `app/agent.py`.

```text
action == bash
  -> execute_bash(command)

action == edit_file_section
  -> edit_file_section(file_path, old_text, new_text)

action == read_tool_output
  -> read_tool_output(output_store, output_id, offset)

action == spawn_subagents
  -> run_subagents(subagent_tasks, evidence=recent_observation_evidence)

action == verify
  -> run_subagents([{agent_name: verify-agent, task: verification_task}], evidence=recent_observation_evidence)

action == yield
  -> return final answer
```

The model only chooses the action and arguments. Python validates and executes
the tool.

## Autonomous Engineering Loop

The VG branch extends the main agent toward a bounded autonomous engineering
loop:

```text
analyze
  -> delegate read-only analysis when useful
  -> synthesize findings
  -> act with safe tools
  -> verify with commands or verify-agent
  -> continue if incomplete
  -> yield only when complete or safely blocked
```

The loop is still the same `AgentSession.run_task()` loop. The new behavior is
expressed through additional structured actions and prompt guidance, not through
a separate orchestrator.

At the start of each user task, the session adds a short bootstrap context with
workspace path rules, safe discovery guidance, and retry guidance. This helps the
agent act on the user's current task instead of spending multiple rounds trying
to discover how to proceed.

## Context And History

`AgentSession.messages` is the in-session memory.

It contains:

```text
system prompt
agent name context
user tasks
structured model decisions
tool observations
final answers
```

This history persists for the lifetime of one running process. Multi-session
history persistence is not required by Assignment 2.

Long tool outputs are stored separately in `AgentSession.output_store`. The
model receives only one page at a time through `read_tool_output()`.

The full session history remains in memory, but individual model calls use a
bounded view controlled by `MAX_CONTEXT_MESSAGES`. The model receives the system
prompt, agent-name context, a compact notice, and the most recent messages.

Sub-agents keep isolated context/history. They do not receive the full main
session. Instead, the main session passes a bounded evidence block built from
recent observations, capped by `SUBAGENT_EVIDENCE_CHARS`.

## Output Pagination

Tool output is limited by `MAX_TOOL_OUTPUT_CHARS`.

When a tool result is longer than the limit:

1. The full result is stored under an id such as `tool-1`.
2. The model receives the first slice.
3. The slice says whether more output exists.
4. The model can call `read_tool_output` with an offset if it needs more.

This prevents huge command outputs from flooding the model context.

## Bash Safety

Bash execution is implemented in `app/shell_tools.py`.

Safety controls:

```text
allowlist only: ls, pwd, cat, echo, head, tail, sed, grep, find
shell=False
cwd=workspace/
timeout=10 seconds
manual y/n approval by default
blocked parent traversal: ..
blocked shell syntax: ; && | > >> < ~ ` $
blocked absolute paths
blocked Windows drive paths
blocked .env and .env.* paths
blocked find -delete / -exec variants
blocked sed -i / --in-place
```

The goal is to allow lightweight inspection while blocking destructive or
secret-exfiltrating commands.

## File Editing Safety

File editing is implemented in `app/file_tools.py`.

The tool edits only one exact section at a time.

Safety controls:

```text
allowed edit roots only: workspace/, app/, README.md, requirements.txt
workspace-relative shorthand accepted
old_text must not be empty
old_text must match exactly once
.env and .env.* blocked
.. traversal blocked by path resolution
Windows absolute host paths blocked
absolute paths outside allowed roots blocked
manual y/n approval by default
```

This avoids broad rewrites and makes each change reviewable before it is written.

## Docker Safety

Docker adds a runtime boundary around the Python safety checks.

The container is configured with:

```text
non-root user: agentuser
read-only root filesystem
dropped Linux capabilities
no-new-privileges
/tmp writable through tmpfs
only selected project paths mounted
.env loaded as environment, not mounted as /agent/.env
```

Docker is not the only guard-rail. It is a second layer in addition to Python
validation and manual approval.

## Hub Agent Flow

Part 3 lives in `app/hub_agent.py` and `app/hub_client.py`.

Startup:

1. `HubAgent` requires `HUB_PASSWORD`.
2. It creates `HubClient`.
3. It creates one long-lived `AgentSession`.
4. If `HUB_SYNC_ON_START=true`, it fetches current hub history from `since=0`.
5. It sets `last_seen` to the newest sequence number.
6. It keeps only the last `HUB_MAX_CONTEXT_MESSAGES` messages.
7. It does not answer old startup messages.

Main loop:

1. Stop if message/model/token cap is reached.
2. Read local console controls if available.
3. If paused, sleep.
4. Fetch new hub messages since `last_seen`.
5. Add messages to rolling hub context.
6. Ignore messages from itself.
7. Consider only messages that mention `AGENT_NAME` or a broadcast trigger.
8. Ask `AgentSession` whether to respond.
9. If the answer is empty or `PASS`, do not post.
10. Otherwise post the response to the hub.

## Hub Collaboration Strategy

The agent is an equal peer, not a manager.

It avoids responding to every message because that can cause a message explosion
when many agents are connected.

Collaboration behavior:

```text
respond only to direct name mentions or configured broadcast triggers
use PASS when there is nothing useful to add
ask for bounded contributions
use temporary task roles only for the current task
extract recent agent names from hub message metadata
combine broadcast triggers with direct mentions when asking for help
avoid secrets and private local context
```

Example bounded request:

```text
all agents / agents: igor-petersson-agent is starting a Hangman task.
Can one agent suggest 5 edge cases and one agent suggest a small safe word list?
Please reply with your agent name and one concrete item.
```

## Hub Budget And Rate Controls

Configured in `app/config.py` and `.env`.

```text
HUB_POLL_SECONDS
HUB_MIN_REQUEST_INTERVAL
HUB_MAX_MESSAGES_SENT
HUB_MAX_MODEL_CALLS
HUB_MAX_TOTAL_TOKENS
HUB_MAX_CONTEXT_MESSAGES
HUB_MAX_POST_CHARS
HUB_INTERACTIVE_CONTROLS
HUB_SYNC_ON_START
HUB_BROADCAST_TRIGGERS
```

Live console controls:

```text
status
pause
resume
max_messages N
max_calls N
max_tokens N
quit
```

These controls make it possible to reduce spending or stop the agent while it is
running.

## Local Token And Cost Awareness

The local `AgentSession` tracks model calls and total tokens across the main
agent and read-only sub-agents.

Configured values:

```text
MAX_TOTAL_TOKENS
TOKEN_WARNING_RATIO
ESTIMATED_COST_PER_1K_TOKENS
```

The session appends usage status to observations so the model can make more
cost-aware choices. When usage passes the warning ratio, the next observation
includes a warning. When the hard token cap is reached, the agent stops before
another model call or before another tool action.

## Blocked Tool Retry Heuristics

The main loop watches observations for blocked or cancelled tool attempts. If
the same kind of blocked/cancelled attempt repeats, it injects a strategy warning
into the next observation.

Configured value:

```text
MAX_BLOCKED_TOOL_ATTEMPTS
```

The warning tells the agent to stop retrying the same pattern and instead use a
simpler allowed command, rely on existing evidence, ask a focused question, or
yield with the safety limitation.

Approval timeout or unavailable stdin is handled separately from explicit user
rejection. A missing approval does not count as a technical tool failure. With
`TOOL_APPROVAL_TIMEOUT_SECONDS=0`, approval prompts block as before. With a
positive timeout, tools remain blocked unless approval arrives before the
timeout.

Approval prompts also route non-approval text back to the main task prompt. This
prevents a file path or next task from being lost if it arrives while an approval
prompt owns stdin. Runtime tracing shows `INPUT` ownership transitions for main
prompt and approval prompt reads.

## Configuration

Main config is loaded in `app/config.py` from environment variables and `.env`.

Important values:

```text
OPENAI_API_KEY
MODEL
AGENT_NAME
MAX_STEPS
MAX_TOOL_OUTPUT_CHARS
REQUIRE_TOOL_CONFIRMATION
DEBUG_AGENT
HUB_URL
HUB_PASSWORD
```

The real `.env` file is ignored by git. `.env.example` documents expected keys
without real secrets.

## Logging And Debug Output

The project currently uses console output instead of persistent logs.

Normal mode:

```text
prints final answer
prints manual approval prompts
```

With `DEBUG_AGENT=true`:

```text
prints structured model decisions
prints tool observations
```

With `DEBUG_RUNTIME_TRACING=true`:

```text
prints concise tagged runtime traces
separates MAIN, SUB, TOOL, VERIFY, BUDGET, and WARN events
shows loop iteration, action choices, tool dispatch, approvals, context trimming,
sub-agent assignments/results, token usage, estimated cost, and yield/stop reasons
```

Hub mode:

```text
prints startup sync status
prints fetch/post failures
prints cap stop reasons
prints status/pause/resume/control feedback
```

No persistent log files are written by the active code.

## Dead Code And Legacy Code

The current Part 3 branch keeps only active runtime files.

The old Part 1 parser/prompt files were removed from this branch because Part 1
is preserved on `master`, and the active Part 2/3 runtime uses structured output
plus `config/system_prompt.txt`.

## Hardcoded Values And Naming

The agent name is configurable through `AGENT_NAME`. The system prompt now refers
to the configured name provided in session context instead of hardcoding a name.

The hub URL defaults to the assignment RunPod URL but can be overridden with
`HUB_URL`.

The hub request interval and max post length are configurable:

```text
HUB_MIN_REQUEST_INTERVAL
HUB_MAX_POST_CHARS
```

The default `AGENT_NAME` remains `igor-petersson-agent` because the assignment
requires a unique, non-generic hub identity.
