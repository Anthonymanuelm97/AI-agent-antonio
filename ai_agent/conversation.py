def start_conversation(agent):
    agent.user_name = input("What is your name? ").strip()
    customer_name = f", {agent.user_name}" if agent.user_name else ""
    print(
        f"Welcome to {agent.business_name}{customer_name}! "
        "How can I assist you today?"
    )

    while True:
        message = input("You: ").strip()
        if message.lower() == "exit":
            break

        response = agent.answer(message)
        print(f"Assistant: {response}")

    agent.show_record()
    