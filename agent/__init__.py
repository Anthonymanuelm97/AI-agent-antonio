import os

from dotenv import load_dotenv
from groq import Groq


class Agent:
    def __init__(self, personality: str, business_name: str = "the coffee shop"):
        load_dotenv()

        self.personality = personality
        self.business_name = business_name
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.record = [
            {"role": "system", "content": self.personality}
        ]

    def answer(self, message: str) -> str:
        self.record.append({"role": "user", "content": message})
        response = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=self.record,
        )
        content = response.choices[0].message.content
        self.record.append({"role": "assistant", "content": content})
        return content

    def show_history(self) -> None:
        for message in self.record:
            if message["role"] != "system":
                print(f"{message['role']}: {message['content']}")
