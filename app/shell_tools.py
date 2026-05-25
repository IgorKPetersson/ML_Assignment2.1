import re
import shlex
import subprocess
from pathlib import Path

from approvals import request_approval
from tracing import trace


ALLOWED_COMMANDS = [
    "ls",
    "pwd",
    "cat",
    "echo",
    "head",
    "tail",
    "sed",
    "grep",
    "find"
]

BLOCKED_PATTERNS = [
    "..",
    ";",
    "&&",
    "|",
    ">",
    ">>",
    "<",
    "~",
    "`",
    "$",
]

BLOCKED_OPTIONS = {
    "find": ["-delete", "-exec", "-execdir", "-ok", "-okdir"],
    "sed": ["-i", "--in-place"],
}

WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "workspace"
WINDOWS_DRIVE_PATH = re.compile(r"^[a-zA-Z]:")


def is_secret_env_path(token):
    name = Path(token).name
    return name == ".env" or name.startswith(".env.")


def validate_command(command):
    if not command or not command.strip():
        return None, "Empty command blocked."

    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return None, f"Blocked unsafe pattern: {pattern}"

    try:
        parts = shlex.split(command)
    except ValueError as e:
        return None, f"Could not parse command safely: {e}"

    if not parts:
        return None, "Empty command blocked."

    base_command = parts[0]

    if base_command not in ALLOWED_COMMANDS:
        return None, f"Command not allowed: {base_command}"

    for token in parts[1:]:
        if token.startswith("/") or token.startswith("\\") or WINDOWS_DRIVE_PATH.match(token):
            return None, f"Blocked absolute path: {token}"
        if is_secret_env_path(token):
            return None, f"Blocked secret environment file path: {token}"

    for blocked_option in BLOCKED_OPTIONS.get(base_command, []):
        if blocked_option in parts[1:]:
            return None, f"Blocked unsafe option for {base_command}: {blocked_option}"

    return parts, None


def execute_bash(command, require_confirmation=True):
    parts, error = validate_command(command)
    if error:
        trace("TOOL", "bash blocked", error)
        return error

    if require_confirmation:
        approval = request_approval("Execute command? [y/n]", command)
        if approval == "rejected":
            return "Command rejected by user."
        if approval == "timeout":
            return "Command approval timed out: no user response received. Command not executed."
        if approval == "unavailable":
            return "Command approval unavailable: no user response received. Command not executed."
        if approval == "empty":
            return "Command approval empty: no approval provided. Command not executed."
        if approval == "invalid":
            return "Command approval invalid: expected y/yes/n/no. Command not executed."
        if approval == "routed_to_main":
            return "Command approval not received: input was routed back to the main task prompt. Command not executed."
        if approval != "approved":
            return "Command cancelled by user."

    try:
        result = subprocess.run(
            parts,
            cwd=WORKSPACE_DIR,
            shell=False,
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout

        if result.stderr:
            output += result.stderr

        if not output:
            output = f"Command finished with exit code {result.returncode}."

        trace("TOOL", "bash completed", f"exit_code={result.returncode} output_chars={len(output)}")
        return output

    except Exception as e:
        trace("TOOL", "bash failed", str(e))
        return str(e)
