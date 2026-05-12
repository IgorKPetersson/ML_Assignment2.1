import re
import shlex
import subprocess
from pathlib import Path


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
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[a-zA-Z]:[\\/]")


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
        if token.startswith("/") or token.startswith("\\") or WINDOWS_ABSOLUTE_PATH.match(token):
            return None, f"Blocked absolute path: {token}"

    for blocked_option in BLOCKED_OPTIONS.get(base_command, []):
        if blocked_option in parts[1:]:
            return None, f"Blocked unsafe option for {base_command}: {blocked_option}"

    return parts, None


def execute_bash(command):
    parts, error = validate_command(command)
    if error:
        return error

    confirm = input(f"\nExecute command? [y/n]\n{command}\n> ")

    if confirm.lower() != "y":
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

        return output

    except Exception as e:
        return str(e)
