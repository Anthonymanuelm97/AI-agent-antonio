from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from ai_agent.clients import reset_client, respond_to
from ai_agent.whatsapp import (
    MAX_INPUT_LENGTH,
    is_daily_limit_allowed,
    is_rate_limit_allowed,
    is_token_valid,
)

WELCOME_MESSAGE = "Hello! How can I help you? Send /reset to start over."

app = FastAPI(title="Customer Service Agent")


class MessageInput(BaseModel):
    client_id: str
    message: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(entry: MessageInput) -> dict[str, str]:
    response = respond_to(entry.client_id, entry.message)
    return {"client_id": entry.client_id, "response": response}


def respond_whatsapp(client_id: str, text: str) -> str:
    print(f"[whatsapp] {client_id}: {text}")

    if len(text) > MAX_INPUT_LENGTH:
        return (
            "Your message is too long. Please keep it to 500 characters or "
            "fewer."
        )

    if text.strip().lower() == "/reset":
        reset_client(client_id)
        return WELCOME_MESSAGE

    if not is_rate_limit_allowed(client_id):
        return (
            "You're sending messages too quickly. Please wait a moment and "
            "try again."
        )

    allowed, limit_message = is_daily_limit_allowed(client_id)
    if not allowed:
        if limit_message is None:
            raise RuntimeError("Daily limit rejection did not include a message.")
        return limit_message

    return respond_to(client_id, text)


@app.post("/whatsapp/chat")
def whatsapp_chat(
    entry: MessageInput,
    bridge_token: str | None = Header(default=None, alias="X-Bridge-Token"),
) -> dict[str, str]:
    if not is_token_valid(bridge_token):
        raise HTTPException(status_code=401, detail="Invalid bridge token.")

    response = respond_whatsapp(entry.client_id, entry.message)
    return {"client_id": entry.client_id, "response": response}
