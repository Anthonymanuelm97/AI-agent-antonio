from ai_agent.agent import Agent
from ai_agent.conversation import start_conversation
from ai_agent.system_prompts import SYSTEM_PROMPT


def main():
    agent = Agent(
        personality=SYSTEM_PROMPT,
        business_name="Cafe Santo Domingo",
    )
    start_conversation(agent)


if __name__ == "__main__":
    main()
