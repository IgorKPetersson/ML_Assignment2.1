import re
from pathlib import Path

from config import BASE_DIR, EDITABLE_PATHS, REQUIRE_TOOL_CONFIRMATION
from shell_tools import is_secret_env_path


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
        return error

    if not old_text:
        return "Edit blocked: old_text must not be empty."

    if not path.exists() or not path.is_file():
        return f"Edit blocked: file does not exist: {file_path}"

    original = path.read_text(encoding="utf-8")
    matches = original.count(old_text)

    if matches == 0:
        return "Edit blocked: old_text was not found exactly once."
    if matches > 1:
        return f"Edit blocked: old_text matched {matches} times. Provide a more specific section."

    if require_confirmation:
        print(f"\nEdit file? [y/n]\n{path}\n")
        print("Old section:\n")
        print(old_text)
        print("\nNew section:\n")
        print(new_text)
        confirm = input("> ")

        if confirm.strip().lower() != "y":
            return "File edit cancelled by user."

    updated = original.replace(old_text, new_text, 1)
    path.write_text(updated, encoding="utf-8")

    return f"Edited one section in {path.relative_to(BASE_DIR)}."
