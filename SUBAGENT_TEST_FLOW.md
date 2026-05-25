# Minimal Sub-Agent Test Flow

This is a small manual test flow for the initial VG sub-agent scaffold.

The goal is to verify that the main agent can:

1. inspect a simple scenario,
2. spawn read-only local sub-agents,
3. receive structured sub-agent results,
4. decide what to do next.

## Fake Scenario

Scenario file:

```text
workspace/subagent_demo/hangman_scenario.txt
```

The scenario describes a tiny Hangman implementation plan with a few deliberate
issues:

- repeated wrong guesses may reduce attempts multiple times,
- uppercase/lowercase guesses may not be normalized,
- win/loss behavior needs verification,
- input validation is underspecified.

## Manual Test Prompt

Run the local agent:

```bash
docker compose run --rm react-agent
```

Then prompt:

```text
Inspect workspace/subagent_demo/hangman_scenario.txt. Use read-only sub-agents
to analyze it in parallel:
- debug-agent should identify likely bugs or failure modes.
- test-agent should suggest focused test cases.
- verify-agent should check whether the scenario satisfies the listed
  requirements.

After receiving their results, summarize the findings and recommend the next
implementation step. Do not edit files yet.
```

## Expected Main-Agent Flow

The exact model behavior can vary, but the expected safe flow is:

```text
1. bash
   Read or inspect subagent_demo/hangman_scenario.txt from workspace/.

2. spawn_subagents
   Run debug-agent, test-agent, and verify-agent with scoped tasks.

3. yield
   Summarize the sub-agent results and recommend next steps.
```

## Expected Safety Behavior

Sub-agents should:

```text
not edit files
not run bash
not spawn other agents
not post to the hub
return structured analysis only
```

The main agent remains responsible for deciding whether to use tools, edit files,
spawn more agents, or yield to the user.

