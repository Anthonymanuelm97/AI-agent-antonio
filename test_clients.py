from dotenv import load_dotenv

from ai_agent.clients import _get_agent_and_lock

load_dotenv()

maria, _ = _get_agent_and_lock("Maria")
maria_again, _ = _get_agent_and_lock("Maria")

pedro, _ = _get_agent_and_lock("Pedro")

print(maria is maria_again)
print(maria is pedro)
