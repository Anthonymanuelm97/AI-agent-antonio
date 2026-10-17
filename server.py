from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from ai_agent.clients import respond_to

load_dotenv()

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
