import json
import os

from openai import OpenAI

from config import (
    AGENT_NAME,
    DEBUG_AGENT,
    MAX_STEPS,
    MAX_TOOL_OUTPUT_CHARS,
    MODEL,
    REQUIRE_TOOL_CONFIRMATION,
    SYSTEM_PROMPT_PATH,
)
from file_tools import edit_file_section
from shell_tools import execute_bash
from structured_output import AGENT_RESPONSE_FORMAT


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_system_prompt():
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def format_tool_output(output, output_store):
    output_id = f"tool-{len(output_store) + 1}"
    output_store[output_id] = output
    return read_tool_output(output_store, output_id, 0)


def read_tool_output(output_store, output_id, offset):
    if output_id not in output_store:
        return f"Unknown output_id: {output_id}"

    output = output_store[output_id]
    offset = max(0, offset)
    end = min(len(output), offset + MAX_TOOL_OUTPUT_CHARS)
    chunk = output[offset:end]

    header = (
        f"Output page for {output_id}: chars {offset}-{end} of {len(output)}.\n"
        f"Use read_tool_output with offset {end} to continue if needed.\n"
    )

    if end >= len(output):
        header += "End of output.\n"
    else:
        header += "Output continues after this page.\n"

    return f"{header}\n{chunk}"


def model_decision(messages):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format=AGENT_RESPONSE_FORMAT,
    )

    content = response.choices[0].message.content
    return json.loads(content)


def observation_for(decision, output_store):
    action = decision["action"]

    if action == "bash":
        command = decision["bash_command"]
        result = execute_bash(command, require_confirmation=REQUIRE_TOOL_CONFIRMATION)
        return format_tool_output(result, output_store)

    if action == "edit_file_section":
        result = edit_file_section(
            decision["file_path"],
            decision["old_text"],
            decision["new_text"],
            require_confirmation=REQUIRE_TOOL_CONFIRMATION,
        )
        return format_tool_output(result, output_store)

    if action == "read_tool_output":
        return read_tool_output(output_store, decision["output_id"], decision["offset"])

    return f"Unknown action: {action}"


class AgentSession:
    def __init__(self):
        self.output_store = {}
        self.messages = [
            {
                "role": "system",
                "content": load_system_prompt(),
            },
            {
                "role": "user",
                "content": f"Agent name: {AGENT_NAME}",
            },
        ]

    def run_task(self, user_task):
        self.messages.append({
            "role": "user",
            "content": f"User task:\n{user_task}",
        })

        for step in range(MAX_STEPS):
            decision = model_decision(self.messages)

            if DEBUG_AGENT:
                print("\nSTRUCTURED MODEL RESPONSE:\n")
                print(json.dumps(decision, indent=2))

            action = decision["action"]

            self.messages.append({
                "role": "assistant",
                "content": json.dumps(decision),
            })

            if action == "yield":
                print("\nAgent finished.\n")
                print(decision["answer"])
                return decision["answer"]

            observation = observation_for(decision, self.output_store)

            if DEBUG_AGENT:
                print("\nOBSERVATION:\n")
                print(observation)

            self.messages.append({
                "role": "user",
                "content": f"Observation:\n{observation}",
            })

        message = "Agent stopped: maximum step count reached."
        print(f"\n{message}\n")
        return message


def run_agent(user_task):
    session = AgentSession()
    return session.run_task(user_task)
