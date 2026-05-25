from approvals import parse_approval_response
from input_router import pop_pending_task_input, push_pending_task_input


def run():
    cases = {
        "y": "approved",
        "Y": "approved",
        "yes": "approved",
        "YES": "approved",
        " yes \n": "approved",
        "y\r\n": "approved",
        "'y'\n": "approved",
        "\"yes\"\n": "approved",
        "\x1b[200~y\x1b[201~\n": "approved",
        "y\x00\n": "approved",
        "\ufeffyes\n": "approved",
        "y\nextra\n": "approved",
        "n": "rejected",
        "N": "rejected",
        "no": "rejected",
        "NO": "rejected",
        " no \n": "rejected",
        "n\r\n": "rejected",
        "'n'\n": "rejected",
        "\"no\"\n": "rejected",
        "\x1b[200~no\x1b[201~\n": "rejected",
        "\n": "empty",
        "   \n": "empty",
        "": "unavailable",
        "maybe\n": "invalid",
    }
    for raw, expected in cases.items():
        actual = parse_approval_response(raw)
        if actual != expected:
            raise AssertionError(
                f"parse_approval_response({raw!r}) returned {actual!r}, "
                f"expected {expected!r}"
            )
    push_pending_task_input("workspace/subagent_demo/hangman_scenario.txt\n")
    pending = pop_pending_task_input()
    if pending != "workspace/subagent_demo/hangman_scenario.txt":
        raise AssertionError(f"pending routed input mismatch: {pending!r}")
    print("approval parser tests passed")


if __name__ == "__main__":
    run()
