from agent import AgentSession


def main():
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
