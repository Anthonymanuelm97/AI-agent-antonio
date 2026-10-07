def start_conversation(agent):
    print(f"Welcome to {agent.business_name}!")
    agent.user_name = input(
        "Assistant: What name should I use for you in this conversation? "
    ).strip() or "User"

    while True:
        message = input("You: ").strip()
        if message.lower() == "exit":
            break

        response = agent.answer(message)
        print(f"Assistant: {response}")

    agent.show_record()
    