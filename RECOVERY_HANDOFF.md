# Recovery Handoff

This file reconstructs the current project state after the chat context was
lost. It is based on the repository, Git history, and existing project docs.

## Immediate Situation

- Current branch: `vg-engineering-agent`
- Latest commit: `3a34e8e add autonomous runtime engineering notes`
- Local branch matches `origin/vg-engineering-agent`
- Tracked working tree change: `.gitignore` only
- No Git stash was present when checked
- No tracked source files appeared deleted or overwritten

Important: this does not recover the lost chat transcript. It gives a practical
map for continuing the work.

## Branch Story

The repository appears to preserve assignment stages as branches:

```text
master
  Part 1 stable secure ReAct bash agent

part-2-structured-agent
  Part 2 structured-output SWE agent

part-3-hub-agent
  Part 3 shared hub/group-chat agent

vg-engineering-agent
  VG extension with autonomous engineering loop and read-only sub-agents
```

Recent commits on `vg-engineering-agent`:

```text
3a34e8e add autonomous runtime engineering notes
c1c56b8 implement autonomous sub-agent orchestration runtime
b5478ec test sub-agent orchestration flow
5b8a91c add sub-agent demo flow and test scenario
115ed8a add minimal sub-agent orchestration scaffold
029a0c7 Document system map and clean Part 3 runtime
```

## What Exists Now

Main runtime files:

```text
app/main.py
app/agent.py
app/structured_output.py
app/config.py
app/shell_tools.py
app/file_tools.py
app/subagents.py
app/hub_client.py
app/hub_agent.py
app/approvals.py
app/input_router.py
app/tracing.py
```

Main documentation and scenarios:

```text
README.md
SYSTEM_MAP.md
AUTONOMOUS_RUNTIME_NOTES.md
SUBAGENT_TEST_FLOW.md
VG_STRESS_TEST_SCENARIO.md
workspace/subagent_demo/hangman_scenario.txt
workspace/sample_project/calculator.py
workspace/sample_project/test_calculator.py
```

## What Was Built

The Part 3 hub agent was extended into a VG-oriented autonomous engineering
agent while keeping the existing Python architecture.

Core architecture:

```text
AgentSession.run_task()
  -> model chooses one structured action
  -> Python validates and dispatches tool
  -> observation is appended to session history
  -> loop continues until yield or safety stop
```

Structured actions now include:

```text
bash
edit_file_section
read_tool_output
spawn_subagents
verify
yield
```

Autonomous engineering flow target:

```text
analyze
  -> delegate to read-only sub-agents when useful
  -> synthesize findings
  -> act with safe tools
  -> verify
  -> continue if incomplete
  -> yield when complete or safely blocked
```

## Sub-Agent Design

The local sub-agents live in `app/subagents.py`.

Roles:

```text
debug-agent
  Looks for likely bugs, failure modes, and suspicious logic.

test-agent
  Suggests focused tests, edge cases, and verification strategy.

verify-agent
  Checks whether the work satisfies stated requirements.
```

Current safety boundary:

```text
sub-agents are read-only
sub-agents do not run bash
sub-agents do not edit files
sub-agents do not spawn other agents
sub-agents do not post to the hub
sub-agents return structured results only
```

The main agent remains responsible for all tool use, edits, and final decisions.

## Key Fixes Already Made

Evidence passing:

- Problem: sub-agents could hallucinate because they only received task text.
- Fix: `AgentSession.recent_observation_evidence()` passes bounded recent tool
  observations into `run_subagents(...)`.
- Config: `SUBAGENT_EVIDENCE_CHARS`

Dedicated verification:

- Problem: the agent used `spawn_subagents` for a single verification pass.
- Fix: added/clarified the `verify` action for one post-edit/post-test/final
  verification pass.

Task bootstrap:

- Problem: the agent spent too many steps rediscovering paths and tool rules.
- Fix: task bootstrap context reminds it that bash paths are relative to
  `workspace/`, while edit paths are project-root relative.

Retry guidance:

- Problem: repeated blocked or cancelled tool attempts burned iterations.
- Fix: repeated blocked/cancelled observations inject strategy guidance.
- Config: `MAX_BLOCKED_TOOL_ATTEMPTS`

Approval handling:

- Problem: missing approval input looked like user rejection.
- Fix: `app/approvals.py` distinguishes approval states.
- Config: `TOOL_APPROVAL_TIMEOUT_SECONDS`

Input routing:

- Problem: approval prompts could consume the next user task.
- Fix: `app/input_router.py` routes non-approval text back to the main prompt.

Tracing:

- Runtime tracing added through `DEBUG_RUNTIME_TRACING=true`.
- Trace tags include `MAIN`, `SUB`, `TOOL`, `VERIFY`, `BUDGET`, `WARN`, and
  `INPUT`.

## Tests And Runs Mentioned In Docs

Real integration test on:

```text
workspace/subagent_demo/hangman_scenario.txt
```

Observed successful action sequence:

```text
bash
spawn_subagents
edit_file_section
spawn_subagents with verify-agent
yield
```

The notes say this led to clearer uncertainty handling and an Acceptance
Criteria section in the Hangman scenario.

Approval parsing tests live in:

```text
app/test_approvals.py
```

Documented approval parsing handled:

```text
y
Y
yes
n
maybe
CRLF / PowerShell-Docker stdin quirks
```

Safety checks were documented as re-run for blocked commands and edit targets,
including `.env`, parent traversal, absolute paths, destructive `find`, and
`sed -i`.

## Important Safety Rules Still In Force

Bash tool safety:

```text
allowlist commands only
shell=False
cwd=workspace/
manual approval by default
blocks .., redirects, pipes, shell variables, backticks, absolute paths
blocks .env and .env.* access
blocks destructive find and in-place sed options
```

File edit safety:

```text
allowed roots only: workspace/, app/, README.md, requirements.txt
exact old_text must match once
manual approval by default
blocks .env and .env.*
blocks parent traversal and unsafe absolute paths
```

Do not commit real secrets from `.env`.

## Current Known Limitation

`python` and `pytest` are not currently in the safe bash allowlist according to
the docs. The agent may be unable to run tests from inside its own safe bash
tool unless the allowlist is intentionally extended. Manual host-side tests can
still be run by the developer outside the agent runtime.

## Suggested Next Moves

1. Preserve this recovery point:

```bash
git status --short
```

Then decide whether to keep or revert only the `.gitignore` change.

2. Run local lightweight tests outside the agent runtime:

```bash
python -m pytest app/test_approvals.py
```

If project dependencies are not installed locally, use Docker.

3. Re-read these docs in this order:

```text
AUTONOMOUS_RUNTIME_NOTES.md
SYSTEM_MAP.md
VG_STRESS_TEST_SCENARIO.md
README.md
```

4. Continue from the VG stress test:

```text
workspace/sample_project/
```

The stress test checks whether the agent can inspect evidence, delegate to
sub-agents, avoid trusting a misleading bug report, edit safely, verify, and
yield only when complete.

## If You Feel Lost

Start with this one sentence:

```text
We are on the VG branch of a Python secure SWE agent, extending Part 3 hub mode
with a bounded autonomous engineering loop and read-only local sub-agents.
```

Then open:

```text
AUTONOMOUS_RUNTIME_NOTES.md
```

That file is currently the closest thing to the lost conversation's technical
memory.
