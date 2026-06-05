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


def create_file(file_path, new_text, require_confirmation=REQUIRE_TOOL_CONFIRMATION):
    path, error = _resolve_project_path(file_path)
    if error:
        trace("TOOL", "file create blocked", error)
        return error

    workspace = (BASE_DIR / "workspace").resolve()
    if path != workspace and workspace not in path.parents:
        trace("TOOL", "file create blocked", f"outside workspace: {file_path}")
        return f"Create blocked: file is outside workspace: {file_path}"

    if not new_text:
        trace("TOOL", "file create blocked", "new_text must not be empty")
        return "Create blocked: new_text must not be empty."

    if path.exists():
        trace("TOOL", "file create blocked", f"file already exists: {file_path}")
        return f"Create blocked: file already exists: {file_path}"

    missing_parent = not path.parent.exists()

    if require_confirmation:
        print(f"\nCreate file? [y/n]\n{path}\n")
        if missing_parent:
            print(f"Missing directories will be created under: {path.parent.relative_to(BASE_DIR)}\n")
        print("Content:\n")
        print(new_text)

        approval = request_approval("Approve file creation? [y/n]", str(path))
        if approval == "rejected":
            return "File creation rejected by user."
        if approval == "timeout":
            return "File creation approval timed out: no user response received. File not created."
        if approval == "unavailable":
            return "File creation approval unavailable: no user response received. File not created."
        if approval == "empty":
            return "File creation approval empty: no approval provided. File not created."
        if approval == "invalid":
            return "File creation approval invalid: expected y/yes/n/no. File not created."
        if approval == "routed_to_main":
            return "File creation approval not received: input was routed back to the main task prompt. File not created."
        if approval != "approved":
            return "File creation cancelled by user."

    if missing_parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(new_text, encoding="utf-8")

    trace("TOOL", "file created", str(path.relative_to(BASE_DIR)))
    if missing_parent:
        return f"Created directory {path.parent.relative_to(BASE_DIR)} and file {path.relative_to(BASE_DIR)}."
    return f"Created file {path.relative_to(BASE_DIR)}."


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
