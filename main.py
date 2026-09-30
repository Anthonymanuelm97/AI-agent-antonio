from agent import Agent


def main():
    agent = Agent(
        personality=(
            "You are a helpful AI assistant that answers clearly, stays concise, "
            "and focuses on practical solutions."
        )
    )
    print(agent.record)


if __name__ == "__main__":
    main()
