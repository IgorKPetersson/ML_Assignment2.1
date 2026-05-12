import subprocess


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
]

def execute_bash(command):
    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return f"Blocked unsafe pattern: {pattern}"

    base_command = command.split()[0]

    if base_command not in ALLOWED_COMMANDS:
        return f"Command not allowed: {base_command}"

    confirm = input(f"\nExecute command? [y/n]\n{command}\n> ")

    if confirm.lower() != "y":
        return "Command cancelled by user."

    try:
        safe_command = f"cd workspace && {command}"

        result = subprocess.run(
            safe_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        return result.stdout

    except Exception as e:
        return str(e)