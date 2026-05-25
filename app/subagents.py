import json
import os
from concurrent.futures import ThreadPoolExecutor, wait

from openai import OpenAI

from config import MAX_SUBAGENTS, MODEL, SUBAGENT_TIMEOUT_SECONDS


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SUBAGENT_ROLES = {
    "debug-agent": (
        "You are debug-agent, a read-only debugging analyst. "
        "Focus on likely bugs, failure modes, and suspicious code paths."
    ),
    "test-agent": (
        "You are test-agent, a read-only testing analyst. "
        "Focus on test cases, edge cases, and verification strategy."
    ),
    "verify-agent": (
        "You are verify-agent, a read-only requirements analyst. "
        "Focus on whether the proposed work satisfies the stated requirements."
    ),
}


SUBAGENT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "subagent_result",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "agent_name": {
                    "type": "string",
                    "enum": ["debug-agent", "test-agent", "verify-agent"],
                },
                "status": {
                    "type": "string",
                    "enum": ["completed", "blocked"],
                },
                "summary": {"type": "string"},
                "findings": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "recommended_next_step": {"type": "string"},
                "confidence": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
            "required": [
                "agent_name",
                "status",
                "summary",
                "findings",
                "recommended_next_step",
                "confidence",
            ],
        },
    },
}


def _run_one_subagent(agent_name, task):
    if agent_name not in SUBAGENT_ROLES:
        return {
            "agent_name": agent_name,
            "status": "blocked",
            "summary": f"Unknown sub-agent: {agent_name}",
            "findings": [],
            "recommended_next_step": "Use debug-agent, test-agent, or verify-agent.",
            "confidence": "high",
            "tokens": 0,
        }

    messages = [
        {
            "role": "system",
            "content": (
                f"{SUBAGENT_ROLES[agent_name]}\n"
                "You are a local read-only sub-agent. Do not run tools, edit files, "
                "spawn other agents, post to any hub, request secrets, or reveal secrets. "
                "Return only the required structured result."
            ),
        },
        {
            "role": "user",
            "content": f"Scoped task:\n{task}",
        },
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format=SUBAGENT_RESPONSE_FORMAT,
        timeout=SUBAGENT_TIMEOUT_SECONDS,
    )
    result = json.loads(response.choices[0].message.content)
    result["tokens"] = 0
    if response.usage is not None:
        result["tokens"] = response.usage.total_tokens or 0
    return result


def run_subagents(subagent_tasks):
    if not subagent_tasks:
        return "No sub-agent tasks were provided."

    scoped_tasks = subagent_tasks[:MAX_SUBAGENTS]
    if not scoped_tasks:
        return "Sub-agent execution skipped because MAX_SUBAGENTS is 0."

    results = []

    executor = ThreadPoolExecutor(max_workers=len(scoped_tasks))
    future_to_task = {
        executor.submit(
            _run_one_subagent,
            item.get("agent_name", ""),
            item.get("task", ""),
        ): item
        for item in scoped_tasks
    }
    try:
        done, not_done = wait(
            future_to_task,
            timeout=SUBAGENT_TIMEOUT_SECONDS,
        )

        for future in done:
            item = future_to_task[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({
                    "agent_name": item.get("agent_name", "unknown"),
                    "status": "blocked",
                    "summary": f"Sub-agent failed: {exc}",
                    "findings": [],
                    "recommended_next_step": "Continue without this sub-agent result.",
                    "confidence": "low",
                    "tokens": 0,
                })

        for future in not_done:
            future.cancel()
            item = future_to_task[future]
            results.append({
                "agent_name": item.get("agent_name", "unknown"),
                "status": "blocked",
                "summary": "Sub-agent timed out.",
                "findings": [],
                "recommended_next_step": "Continue without this sub-agent result.",
                "confidence": "low",
                "tokens": 0,
            })
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return json.dumps(
        {
            "subagent_results": results,
            "requested": len(subagent_tasks),
            "executed": len(scoped_tasks),
            "max_subagents": MAX_SUBAGENTS,
        },
        indent=2,
    )
