from collections import deque

from tracing import trace


_pending_task_inputs = deque()


def push_pending_task_input(raw_input):
    value = raw_input.strip()
    if not value:
        return
    _pending_task_inputs.append(value)
    trace("INPUT", "routed approval input back to main prompt", repr(value), limit=220)


def pop_pending_task_input():
    if not _pending_task_inputs:
        return ""
    value = _pending_task_inputs.popleft()
    trace("INPUT", "main prompt consumed routed input", repr(value), limit=220)
    return value


def has_pending_task_input():
    return bool(_pending_task_inputs)
