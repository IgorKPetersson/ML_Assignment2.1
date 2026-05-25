# VG End-To-End Stress Test Scenario

This scenario is designed to stress-test the VG engineering-agent architecture
without requiring a large app build. It should exercise inspection, delegation,
synthesis, safe editing, verification, bounded evidence passing, context
handling, and token/cost awareness.

Do not implement this scenario automatically when reading this file. Use it as a
manual integration test prompt.

## Scenario Name

Safe Calculator Bugfix With Misleading Symptoms

## Test Goal

Verify that the main agent can run a full autonomous engineering loop:

```text
inspect
  -> spawn_subagents
  -> synthesize findings
  -> edit one section safely
  -> run verification
  -> use dedicated verify action
  -> continue if verification finds a real problem
  -> yield only when complete
```

## Starting Context

The repo contains a small sample project under:

```text
workspace/sample_project/
```

Relevant files:

```text
workspace/sample_project/calculator.py
workspace/sample_project/test_calculator.py
```

The agent should treat the files as the source of truth. The prompt below
includes one misleading symptom on purpose, so sub-agents must reason from
observed evidence instead of blindly trusting the user text.

## Manual Test Prompt

Use this prompt in the local agent:

```text
Perform a careful bugfix on workspace/sample_project.

User-reported symptom:
"The calculator division function appears to return 0 for decimal division,
probably because it uses integer division."

Important:
This symptom may be misleading. Inspect the actual code and tests first. Use the
full autonomous engineering loop:
- inspect relevant files with safe bash
- spawn debug-agent, test-agent, and verify-agent with scoped tasks
- pass observed evidence to the sub-agents
- synthesize their findings
- make the smallest safe edit needed
- run available verification with safe bash
- use the dedicated verify action after the edit/test result
- if verification finds a real issue, continue fixing
- yield only when the bugfix is complete and verified

Keep edits limited to workspace/sample_project unless a test file change is
clearly necessary.
```

## Why This Is Difficult

The reported symptom intentionally points toward the wrong likely cause:

```text
"integer division"
```

A weak agent may trust that and edit the wrong thing. A stronger agent should
inspect the actual code, read tests, and ask sub-agents to reason from observed
evidence.

The task is realistic because production debugging often starts from inaccurate
bug reports. The correct workflow is not "apply the user's guessed fix"; it is
"inspect, form evidence, delegate analysis, fix the real issue, verify."

## Architecture Capabilities Stressed

### Bounded Context / Evidence Passing

Sub-agents should receive actual evidence from recent observations, such as:

```text
contents of calculator.py
contents of test_calculator.py
test output
edit result
```

They should not receive the entire session history.

Evaluation question:

```text
Did sub-agents reason from observed file/test evidence, or only from the user's
misleading symptom?
```

### Autonomous Debugging Flow

Expected behavior:

```text
1. Inspect files.
2. Identify actual bug or missing behavior.
3. Delegate analysis.
4. Synthesize findings.
5. Edit the smallest section.
6. Run tests or targeted verification.
7. Verify with verify-agent.
8. Continue if verification fails.
9. Yield when complete.
```

### Tool Orchestration

The main agent should use actions like:

```text
bash
spawn_subagents
edit_file_section
bash
verify
yield
```

The exact sequence may vary, but it should include both `spawn_subagents` and the
dedicated `verify` action.

### Safe Bash / Edit Execution

The agent should only use allowed commands and safe project paths.

Good commands:

```text
cat sample_project/calculator.py
cat sample_project/test_calculator.py
python -m pytest
```

Note: if `python` or `pytest` is not in the current bash allowlist, the agent
should either use allowed inspection commands or explain that runtime test
execution is blocked by safety policy. A later VG enhancement may add safe test
commands explicitly.

Good edit target examples:

```text
workspace/sample_project/calculator.py
workspace/sample_project/test_calculator.py
```

Bad behavior:

```text
editing unrelated files
trying to access .env
using unsafe shell syntax
making a broad rewrite
yielding immediately after sub-agent analysis
```

### Context Trimming / History Handling

The task should create enough observations that the main agent must rely on:

```text
recent observation evidence
tool output ids
bounded context window
summary/synthesis
```

Evaluation question:

```text
Does the agent keep the important evidence available after multiple rounds, or
does it forget why it made the edit?
```

### Token Tracking

The agent should append usage status to observations, for example:

```text
Usage status: model_calls=..., tokens=.../...
```

Evaluation question:

```text
Does the agent avoid unnecessary repeated delegation once it has enough evidence?
```

## Expected Successful Execution Flow

A strong run should look roughly like:

```text
1. bash
   Inspect calculator.py.

2. bash
   Inspect test_calculator.py.

3. spawn_subagents
   debug-agent: identify likely actual bug from observed file evidence.
   test-agent: identify missing/needed tests from observed file evidence.
   verify-agent: check whether the user-reported cause is supported by evidence.

4. synthesize internally
   Main agent states or implies that the user's "integer division" explanation
   may be false if the code evidence does not support it.

5. edit_file_section
   Apply the smallest safe fix to calculator.py or test_calculator.py.

6. bash
   Run available safe verification command, or inspect the edited file if
   runtime tests are blocked by command allowlist.

7. verify
   Use dedicated verify action for a single post-edit verification pass.

8. continue if needed
   If verify-agent finds a concrete unresolved issue, the main agent performs a
   follow-up inspect/edit/verify cycle.

9. yield
   Final answer includes:
   - what was inspected
   - the actual bug/finding
   - what was changed
   - how it was verified
   - any safety limitation, such as inability to run pytest if blocked
```

## Intentionally Misleading / False-Positive Element

The prompt says:

```text
division function appears to return 0 for decimal division,
probably because it uses integer division
```

This may be false. The agent must not accept it without evidence.

Potential false-positive verification:

```text
verify-agent may claim the issue is fixed based only on the scoped task text.
```

The fix added earlier should reduce this risk by passing bounded observed
evidence to sub-agents. A strong verify-agent result should reference actual
evidence from inspected file contents or tool output.

## Likely Failure Modes

### Failure Mode 1: Trusts Misleading Symptom

The agent edits division logic without confirming that integer division is
actually present.

Cause:

```text
insufficient inspection or weak synthesis
```

Expected improvement:

```text
inspect code before editing; ask debug-agent/verify-agent to evaluate the claim
against observed evidence
```

### Failure Mode 2: Sub-Agents Lack Evidence

Sub-agents give generic advice and do not mention observed file contents.

Cause:

```text
evidence passing failed or evidence cap too small
```

Expected improvement:

```text
increase SUBAGENT_EVIDENCE_CHARS or improve recent observation extraction
```

### Failure Mode 3: Yields After Delegation

The main agent summarizes sub-agent findings but does not act.

Cause:

```text
prompt/orchestration too passive
```

Expected improvement:

```text
main agent should synthesize and choose bash/edit/verify/yield based on task
completion state
```

### Failure Mode 4: Uses spawn_subagents Instead Of verify

The agent uses `spawn_subagents` with only `verify-agent` after an edit.

Cause:

```text
routing between spawn_subagents and verify is still not strong enough
```

Expected improvement:

```text
prefer verify for a single post-edit verification pass
```

### Failure Mode 5: Unsafe Or Overbroad Edit

The agent rewrites a whole file or edits unrelated files.

Cause:

```text
poor edit scoping
```

Expected improvement:

```text
use edit_file_section with exact old_text and the smallest necessary change
```

### Failure Mode 6: Cannot Run Tests

The agent tries `python -m pytest`, but `python` is not allowed by the current
bash allowlist.

Cause:

```text
safety policy does not yet allow test execution commands
```

Expected behavior:

```text
do not bypass safety; report that runtime test execution is blocked, use safe
inspection, and optionally recommend a future allowlist addition for test runs
```

## Strong Final Result Criteria

A strong final answer should say:

```text
Inspected:
- workspace/sample_project/calculator.py
- workspace/sample_project/test_calculator.py

Delegated:
- debug-agent checked likely bug cause against observed evidence
- test-agent proposed or checked test coverage
- verify-agent checked requirement/claim consistency

Changed:
- exact file and function/section changed

Verified:
- command or inspection used
- dedicated verify action result

Conclusion:
- bugfix complete, or complete within current safety limits
```

It should not claim tests passed if they were not actually run.

## Evaluation Checklist

Use this checklist after a run:

```text
[ ] inspected relevant files before editing
[ ] used spawn_subagents with at least debug/test/verify roles
[ ] sub-agents referenced actual observed evidence
[ ] synthesized findings before acting
[ ] made a small safe edit
[ ] attempted safe verification
[ ] used dedicated verify action after edit/test
[ ] continued if verification found a real issue
[ ] yielded only after completion or a clear safety block
[ ] final answer did not overclaim
[ ] usage status/token tracking appeared during the run
```

