import json
import os
from groq import Groq

from agente_ai_builder.tools import HERRAMIENTAS, execute_tool


class Agent:
    def __init__(self, personality: str, business_name: str = "the coffee shop"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.business_name = business_name
        self.record = [
            {"role": "system", "content": personality}
        ]

    def answer(self, message: str) -> str:
        self.record.append({"role": "user", "content": message})

        while True:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=self.record,
                tools=HERRAMIENTAS,
                tool_choice="auto",
            )
            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls

            if not tool_calls:
                content = assistant_message.content or ""
                self.record.append({"role": "assistant", "content": content})
                return content

            self.record.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in tool_calls
                    ],
                }
            )

            for tool_call in tool_calls:
                try:
                    arguments = tool_call.function.arguments
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be a JSON object.")
                    result = execute_tool(tool_call.function.name, arguments)
                except (json.JSONDecodeError, TypeError, ValueError):
                    result = (
                        "The tool request could not be processed because its "
                        "arguments were invalid or incomplete."
                    )
                except Exception:
                    result = (
                        "The requested business information could not be "
                        "retrieved at this time."
                    )

                self.record.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": result,
                    }
                )

    def show_record(self) -> None:
        for message in self.record:
            if (
                (
                    message["role"] == "user"
                    or (
                        message["role"] == "assistant"
                        and not message.get("tool_calls")
                    )
                )
                and message.get("content")
            ):
                print(f"{message['role']}: {message['content']}")