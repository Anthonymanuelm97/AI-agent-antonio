from pathlib import Path

from agent import Agent
from conversation import start_conversation


def main():
    personality = Path(__file__).with_name("SYSTEM_PROMPTS").read_text(
        encoding="utf-8"
    )
    agent = Agent(
        personality=personality,
        business_name="the coffee shop",
    )
    start_conversation(agent)


if __name__ == "__main__":
    main()
