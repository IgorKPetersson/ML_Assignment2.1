from agent import run_agent


def main():

    user_task = input("What should the agent do?\n> ")

    run_agent(user_task)


if __name__ == "__main__":
    main()