import os

from dotenv import load_dotenv
from groq import Groq


class Agent:
    def __init__(self, personality: str):
        load_dotenv()

        self.personality = personality
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.record = [
            {"role": "system", "content": self.personality}
        ]
