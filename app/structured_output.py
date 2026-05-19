AGENT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "agent_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "thought": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["bash", "edit_file_section", "read_tool_output", "yield"],
                },
                "bash_command": {"type": "string"},
                "file_path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
                "output_id": {"type": "string"},
                "offset": {"type": "integer"},
                "answer": {"type": "string"},
            },
            "required": [
                "thought",
                "action",
                "bash_command",
                "file_path",
                "old_text",
                "new_text",
                "output_id",
                "offset",
                "answer",
            ],
        },
    },
}
