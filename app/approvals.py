import select
import sys
import re

from config import TOOL_APPROVAL_TIMEOUT_SECONDS
from input_router import push_pending_task_input
from tracing import trace


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def normalize_approval_response(response):
    if response == "":
        return ""

    normalized = ANSI_ESCAPE.sub("", response)
    normalized = normalized.replace("\x00", "")
    normalized = normalized.replace("\ufeff", "")
    normalized = normalized.strip().lower()
    normalized = normalized.strip("\"'")

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if lines:
        normalized = lines[0]

    return normalized


def parse_approval_response(response):
    if response == "":
        return "unavailable"

    normalized = normalize_approval_response(response)
    if normalized in {"y", "yes"}:
        return "approved"
    if normalized in {"n", "no"}:
        return "rejected"
    if normalized == "":
        return "empty"
    return "invalid"


def request_approval(prompt, detail, section="TOOL"):
    trace("INPUT", "stdin owner -> approval", detail)
    trace(section, "approval prompt start", detail)
    trace(section, "waiting for approval", detail)
    print(f"\n{prompt}\n{detail}\n> ", end="", flush=True)

    try:
        if TOOL_APPROVAL_TIMEOUT_SECONDS > 0:
            ready, _, _ = select.select(
                [sys.stdin],
                [],
                [],
                TOOL_APPROVAL_TIMEOUT_SECONDS,
            )
            if not ready:
                trace(
                    section,
                    "approval timeout",
                    f"timeout_seconds={TOOL_APPROVAL_TIMEOUT_SECONDS}",
                )
                trace(section, "approval prompt end", "state=timeout")
                trace("INPUT", "stdin owner released by approval", "state=timeout")
                return "timeout"

        response = sys.stdin.readline()
    except (EOFError, OSError):
        trace(section, "approval unavailable", "stdin unavailable")
        trace(section, "approval prompt end", "state=unavailable")
        trace("INPUT", "stdin owner released by approval", "state=unavailable")
        return "unavailable"

    normalized = normalize_approval_response(response)
    trace(section, "approval raw input", repr(response), limit=220)
    trace(section, "approval normalized input", repr(normalized), limit=220)
    parsed = parse_approval_response(response)
    trace(section, "approval response parsed", f"state={parsed}")

    if parsed == "approved":
        trace(section, "approval granted", detail)
        trace(section, "approval prompt end", "state=approved")
        trace("INPUT", "stdin owner released by approval", "state=approved")
        return "approved"

    if parsed == "rejected":
        trace(section, "approval rejected", detail)
        trace(section, "approval prompt end", "state=rejected")
        trace("INPUT", "stdin owner released by approval", "state=rejected")
        return "rejected"

    if parsed == "unavailable":
        trace(section, "approval unavailable", "no stdin response")
        trace(section, "approval prompt end", "state=unavailable")
        trace("INPUT", "stdin owner released by approval", "state=unavailable")
        return "unavailable"

    if parsed == "empty":
        trace(section, "approval empty", "empty input")
        trace(section, "approval prompt end", "state=empty")
        trace("INPUT", "stdin owner released by approval", "state=empty")
        return "empty"

    push_pending_task_input(response)
    trace(
        section,
        "approval input was not approval",
        "routed to main prompt; expected y/yes/n/no",
    )
    trace(section, "approval prompt end", "state=routed_to_main")
    trace("INPUT", "stdin owner released by approval", "state=routed_to_main")
    return "routed_to_main"
