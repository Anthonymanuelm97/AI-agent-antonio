import threading

from .agent import Agent
from .system_prompts import SYSTEM_PROMPT

_agents: dict[str, Agent] = {}
_locks: dict[str, threading.Lock] = {}
_general_lock = threading.Lock()


def _get_agent_and_lock(
    client_id: str,
) -> tuple[Agent, threading.Lock]:
    with _general_lock:
        if client_id not in _agents:
            _agents[client_id] = Agent(
                personality=SYSTEM_PROMPT,
                client_id=client_id,
            )
            _locks[client_id] = threading.Lock()

        return _agents[client_id], _locks[client_id]


def respond_to(client_id: str, message: str) -> str:
    agent, lock = _get_agent_and_lock(client_id)

    with lock:
        return agent.answer(message)
