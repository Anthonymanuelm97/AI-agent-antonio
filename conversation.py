def start_conversation(agent):
    print(f"Welcome to {agent.business_name}!")

    while True:
        message = input("You: ").strip()
        if message.lower() == "exit":
            break

        response = agent.answer(message)
        print(f"Assistant: {response}")

    agent.show_record()
    