from config import DEBUG_RUNTIME_TRACING


COLORS = {
    "MAIN": "\033[36m",
    "SUB": "\033[35m",
    "TOOL": "\033[33m",
    "VERIFY": "\033[34m",
    "BUDGET": "\033[32m",
    "WARN": "\033[31m",
    "INPUT": "\033[37m",
}
RESET = "\033[0m"


def _short(text, limit=180):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def trace(section, message, detail="", limit=180):
    if not DEBUG_RUNTIME_TRACING:
        return
    color = COLORS.get(section, "")
    prefix = f"[{section}]"
    if color:
        prefix = f"{color}{prefix}{RESET}"
    line = f"{prefix} {message}"
    if detail:
        line += f" | {_short(detail, limit)}"
    print(line)
