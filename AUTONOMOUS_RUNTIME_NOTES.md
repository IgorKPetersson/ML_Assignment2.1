# Autonomous Runtime Notes

This document summarizes the autonomous engineering-agent runtime work on the
`vg-engineering-agent` branch.

## What We Built

We evolved the Part 3 hub/agent system into a VG-oriented autonomous engineering
agent without redesigning the project.

The main agent still uses the existing `AgentSession` loop in `app/agent.py`.
The loop now supports a fuller engineering cycle:

```text
analyze
  -> delegate
  -> synthesize
  -> act
  -> verify
  -> continue if needed
  -> yield when complete
```

Main additions:

- `spawn_subagents` structured action
- `verify` structured action
- read-only local sub-agents in `app/subagents.py`
- `debug-agent`, `test-agent`, and `verify-agent`
- bounded recent evidence passing from main-agent observations to sub-agents
- context trimming for model calls through `MAX_CONTEXT_MESSAGES`
- token/cost awareness through `MAX_TOTAL_TOKENS`, `TOKEN_WARNING_RATIO`, and
  `ESTIMATED_COST_PER_1K_TOKENS`
- runtime tracing through `DEBUG_RUNTIME_TRACING`
- approval-state handling through `app/approvals.py`
- stdin routing through `app/input_router.py`
- stress-test documentation in `VG_STRESS_TEST_SCENARIO.md`

Sub-agents are intentionally read-only:

- they do not edit files
- they do not run bash
- they do not spawn other agents
- they do not post to the hub
- they return structured JSON results only

The main agent remains responsible for safe tools, edits, verification, and
final yield decisions.

## Runtime Tracing

Runtime tracing is controlled by:

```env
DEBUG_RUNTIME_TRACING=true
```

Trace sections:

```text
[MAIN]    main-agent loop, decisions, context trimming, yield/stop reasons
[SUB]     sub-agent spawning, task assignment, summaries, timeouts
[TOOL]    bash/edit/read dispatch and approvals
[VERIFY]  dedicated verification calls
[BUDGET]  token/cost accounting
[WARN]    budget warnings and stop conditions
[INPUT]   stdin ownership and routed input
```

The goal is terminal-friendly visibility into the autonomous loop without
printing full raw model JSON unless `DEBUG_AGENT=true`.

## Real Integration Test: Hangman Scenario

We ran a real Docker/OpenAI integration test against:

```text
workspace/subagent_demo/hangman_scenario.txt
```

The requested loop was:

```text
inspect scenario
  -> spawn debug/test/verify sub-agents
  -> synthesize findings
  -> edit the scenario file
  -> verify afterward
  -> yield when complete
```

Observed action sequence:

```text
bash
spawn_subagents
edit_file_section
spawn_subagents with verify-agent
yield
```

The agent inspected the file with:

```text
head -40 subagent_demo/hangman_scenario.txt
```

It then spawned:

```text
debug-agent
test-agent
verify-agent
```

It edited the scenario by replacing the vague `Known uncertainty` section with
clearer uncertainty handling and adding an `Acceptance Criteria` section.

Afterward, it ran a verification pass with `verify-agent` and yielded only after
verification completed.

Final reported usage from that run:

```text
model_calls=4
tokens=12967/50000
```

## Bugs Found And Fixed

### 1. Sub-Agents Had Too Little Evidence

Observed problem:

`verify-agent` initially claimed the Hangman scenario already had explicit
Acceptance Criteria even though the inspected file did not.

Likely cause:

```text
Sub-agents only received scoped task text.
They did not receive actual observed file contents from the main agent.
```

Fix:

- added `SUBAGENT_EVIDENCE_CHARS`
- added `AgentSession.recent_observation_evidence()`
- passed bounded recent observations into `run_subagents(...)`
- updated `app/subagents.py` so each sub-agent receives:

```text
Scoped task
Bounded evidence from the main agent's recent observations
```

This preserves isolated sub-agent context while grounding them in real evidence.

### 2. Agent Used `spawn_subagents` For Single Verification

Observed problem:

After editing, the model used:

```text
spawn_subagents -> verify-agent
```

instead of the dedicated:

```text
verify
```

Fix:

- added clearer prompt routing:
  - use `spawn_subagents` for broad parallel analysis
  - prefer `verify` for a single post-edit, post-test, or final completion check
- documented this in `README.md` and `SYSTEM_MAP.md`

### 3. Agent Spent Too Long Discovering How To Execute The Task

Observed problem:

During runtime tracing, the agent spent too many iterations trying to discover
how to execute the stress-test scenario instead of acting on the user's concrete
task.

Root cause:

```text
Insufficient task bootstrap context.
The agent needed stronger startup grounding for workspace paths and safe
inspection behavior.
```

Fix:

- added `TASK_BOOTSTRAP_CONTEXT` in `app/agent.py`
- every user task now includes guidance such as:
  - bash runs from `workspace/`
  - use paths like `sample_project/calculator.py` for bash
  - use paths like `workspace/sample_project/calculator.py` for edits
  - inspect user-named files first
  - avoid repeated blocked/cancelled exploration loops

### 4. Repeated Blocked/Cancelled Attempts Caused Retry Loops

Observed problem:

Blocked or cancelled tool attempts caused the agent to shift strategy
incorrectly or burn tokens retrying similar attempts.

Fix:

- added `MAX_BLOCKED_TOOL_ATTEMPTS`
- added `AgentSession.failure_guidance(...)`
- when repeated blocked/cancelled tool attempts are observed, the main loop
  injects a strategy warning:

```text
Strategy warning: repeated blocked or cancelled tool attempts were observed.
Do not retry the same command/edit pattern...
```

Runtime trace example:

```text
[WARN] blocked/cancelled tool attempt observed | count=2 marker=Command not allowed:
[WARN] strategy warning injected
```

### 5. Approval Silence Was Treated As User Cancellation

Observed problem:

In autonomous runs, the agent waited for approval but received no usable input.
The old behavior treated this like:

```text
Command cancelled by user.
```

This caused incorrect strategy shifts.

Fix:

- added `app/approvals.py`
- added explicit approval states:

```text
approved
rejected
timeout
unavailable
empty
invalid
```

Config:

```env
TOOL_APPROVAL_TIMEOUT_SECONDS=0
```

`0` preserves blocking approval prompts. A positive value enables timeout.

Runtime tracing now shows:

```text
[TOOL] waiting for approval
[TOOL] approval timeout
[TOOL] approval unavailable
[WARN] approval blocked state observed
```

Approval timeout/unavailable no longer counts as a technical tool failure.

### 6. Valid Approval Input Was Sometimes Parsed Incorrectly

Observed problem:

Runtime tracing showed valid approval input being treated incorrectly.

Fix:

- added `normalize_approval_response(...)`
- expanded approval parsing to handle:
  - `y`
  - `yes`
  - `n`
  - `no`
  - uppercase variants
  - whitespace
  - CRLF from Docker/PowerShell
  - quoted input
  - ANSI/bracketed paste wrappers
  - null bytes
  - UTF BOM
  - multi-line input by using the first meaningful line

Test file:

```text
app/test_approvals.py
```

Verified Docker stdin traces:

```text
approval raw input | 'y\r\n'
approval normalized input | 'y'
approval response parsed | state=approved

approval raw input | 'Y\r\n'
approval normalized input | 'y'
approval response parsed | state=approved

approval raw input | 'yes\r\n'
approval normalized input | 'yes'
approval response parsed | state=approved

approval raw input | 'n\r\n'
approval normalized input | 'n'
approval response parsed | state=rejected

approval raw input | 'maybe\r\n'
approval normalized input | 'maybe'
approval response parsed | state=invalid
```

### 7. Approval Prompt Consumed The Next Task Input

Observed problem:

Runtime tracing showed:

```text
approval raw input | 'workspace/subagent_demo/hangman_scenario.txt\n'
```

This meant the approval prompt consumed a line that was intended for the next
main task prompt.

Root cause:

```text
Approval prompts and the main task prompt share one stdin stream.
If the user typed the next task while approval was active, approval consumed it.
```

Fix:

- added `app/input_router.py`
- non-approval text received by approval is routed back to the main prompt
- `main.py` checks routed pending task input before reading stdin again

Runtime trace after the fix:

```text
[INPUT] stdin owner -> approval | demo
[TOOL] approval prompt start | demo
[TOOL] approval raw input | 'workspace/subagent_demo/hangman_scenario.txt\r\n'
[TOOL] approval normalized input | 'workspace/subagent_demo/hangman_scenario.txt'
[TOOL] approval response parsed | state=invalid
[INPUT] routed approval input back to main prompt | 'workspace/subagent_demo/hangman_scenario.txt'
[TOOL] approval input was not approval | routed to main prompt; expected y/yes/n/no
[TOOL] approval prompt end | state=routed_to_main
[INPUT] stdin owner released by approval | state=routed_to_main
[INPUT] main prompt consumed routed input | 'workspace/subagent_demo/hangman_scenario.txt'
```

The tool is not executed unless approval is explicit, and the user's next task
input is not lost.

## Safety Checks Re-Run

After the runtime changes, existing safety checks were re-run.

Bash validation still blocks:

```text
rm -rf .
cat ../.env
sed -i ...
cat C:/Users/test/.env
find . -delete
```

File edit validation still blocks:

```text
.env
../.env
C:/Users/test/.env
/agent/config/system_prompt.txt
```

The changes did not loosen command validation or file-edit restrictions.

## Current Known Notes

- Sub-agents are still read-only by design.
- Runtime tests with real model calls can consume tokens quickly.
- `workspace/subagent_demo/hangman_scenario.txt` was modified during the real
  integration test and now contains the added Acceptance Criteria section.
- `python`/`pytest` are not in the current bash allowlist, so runtime test
  execution remains restricted unless the allowlist is intentionally extended.

