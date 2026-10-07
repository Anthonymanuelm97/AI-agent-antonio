import json
import os
from groq import Groq

from agente_ai_builder.tools import HERRAMIENTAS, execute_tool

MODEL = "openai/gpt-oss-120b"


class Agent:
    def __init__(self, personality: str, business_name: str = "the coffee shop"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.business_name = business_name
        self.user_name = ""
        self.record = [
            {"role": "system", "content": personality}
        ]

    def _messages_for_model(self):
        messages = self.record.copy()
        if self.user_name:
            system_message = messages[0].copy()
            system_message["content"] = (
                f"{system_message['content']}\n\n"
                f"The customer's name is {self.user_name}. Remember their name "
                "and use it naturally when speaking with them."
            )
            messages[0] = system_message
        return messages

    def answer(self, message: str) -> str:
        self.record.append({"role": "user", "content": message})

        while True:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self._messages_for_model(),
                tools=HERRAMIENTAS,
                tool_choice="auto",
            )
            print(
                f"[tokens] enviados: {response.usage.prompt_tokens}, "
                f"generados: {response.usage.completion_tokens}"
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

            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self._messages_for_model(),
            )
            assistant_message = response.choices[0].message
            content = assistant_message.content or ""
            self.record.append({"role": "assistant", "content": content})
            return content

    def show_record(self) -> None:
        display_name = self.user_name or "User"

        print("========================================")
        print("          CONVERSATION HISTORY")
        print("========================================")

        for message in self.record:
            role = message.get("role")
            if role not in ("user", "assistant"):
                continue

            content = message.get("content")
            if content:
                label = display_name if role == "user" else "Assistant"
                print(f"\n{label}:\n{content}")
                print("\n----------------------------------------")

        print("\n========================================")
        print("           END OF CONVERSATION HISTORY")
        print("========================================")