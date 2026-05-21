import argparse

from agent import AgentSession
from hub_agent import HubAgent


def parse_args():
    parser = argparse.ArgumentParser(description="Assignment 2 agent")
    parser.add_argument(
        "--hub",
        action="store_true",
        help="Run the Part 3 shared hub agent instead of the local Part 2 CLI.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.hub:
        try:
            HubAgent().run()
        except ValueError as e:
            print(f"Could not start hub agent: {e}")
        return

    session = AgentSession()

    print("Agent session started. Type 'exit' or 'quit' to stop.")

    while True:
        user_task = input("\nWhat should the agent do?\n> ").strip()

        if user_task.lower() in {"exit", "quit"}:
            print("Agent session ended.")
            break

        if not user_task:
            continue

        session.run_task(user_task)


if __name__ == "__main__":
    main()
