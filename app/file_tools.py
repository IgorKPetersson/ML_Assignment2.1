import re
from pathlib import Path

from approvals import request_approval
from config import BASE_DIR, EDITABLE_PATHS, REQUIRE_TOOL_CONFIRMATION
from shell_tools import is_secret_env_path
from tracing import trace


WINDOWS_ABSOLUTE_PATH = re.compile(r"^[a-zA-Z]:[\\/]")


def _resolve_project_path(file_path):
    if WINDOWS_ABSOLUTE_PATH.match(file_path):
        return None, f"File is outside editable paths: {file_path}"

    requested = Path(file_path)
    if requested.is_absolute():
        candidates = [requested.resolve()]
    else:
        candidates = [
            (BASE_DIR / requested).resolve(),
            (BASE_DIR / "workspace" / requested).resolve(),
        ]

    candidate = None
    for possible_path in candidates:
        if _is_editable(possible_path):
            candidate = possible_path
            break

    if candidate is None:
        return None, f"File is outside editable paths: {file_path}"

    if any(is_secret_env_path(part) for part in candidate.parts):
        return None, f"Refusing to edit secret environment file: {file_path}"

    return candidate, None


def _is_editable(candidate):
    for allowed in EDITABLE_PATHS:
        allowed = allowed.resolve()
        if allowed.is_file() and candidate == allowed:
            return True
        if allowed.is_dir() and (candidate == allowed or allowed in candidate.parents):
            return True
    return False


def edit_file_section(file_path, old_text, new_text, require_confirmation=REQUIRE_TOOL_CONFIRMATION):
    path, error = _resolve_project_path(file_path)
    if error:
        trace("TOOL", "file edit blocked", error)
        return error

    if not old_text:
        trace("TOOL", "file edit blocked", "old_text must not be empty")
        return "Edit blocked: old_text must not be empty."

    if not path.exists() or not path.is_file():
        trace("TOOL", "file edit blocked", f"file does not exist: {file_path}")
        return f"Edit blocked: file does not exist: {file_path}"

    original = path.read_text(encoding="utf-8")
    matches = original.count(old_text)

    if matches == 0:
        trace("TOOL", "file edit blocked", "old_text not found exactly once")
        return "Edit blocked: old_text was not found exactly once."
    if matches > 1:
        trace("TOOL", "file edit blocked", f"old_text matched {matches} times")
        return f"Edit blocked: old_text matched {matches} times. Provide a more specific section."

    if require_confirmation:
        print(f"\nEdit file? [y/n]\n{path}\n")
        print("Old section:\n")
        print(old_text)
        print("\nNew section:\n")
        print(new_text)

        approval = request_approval("Approve file edit? [y/n]", str(path))
        if approval == "rejected":
            return "File edit rejected by user."
        if approval == "timeout":
            return "File edit approval timed out: no user response received. File not edited."
        if approval == "unavailable":
            return "File edit approval unavailable: no user response received. File not edited."
        if approval == "empty":
            return "File edit approval empty: no approval provided. File not edited."
        if approval == "invalid":
            return "File edit approval invalid: expected y/yes/n/no. File not edited."
        if approval == "routed_to_main":
            return "File edit approval not received: input was routed back to the main task prompt. File not edited."
        if approval != "approved":
            return "File edit cancelled by user."

    updated = original.replace(old_text, new_text, 1)
    path.write_text(updated, encoding="utf-8")

    trace("TOOL", "file edit completed", str(path.relative_to(BASE_DIR)))
    return f"Edited one section in {path.relative_to(BASE_DIR)}."
