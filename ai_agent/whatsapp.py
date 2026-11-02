import hmac
import os
import threading
import time
from collections import defaultdict, deque
from datetime import date

MAX_INPUT_LENGTH = 500
MAX_MESSAGES = 6
WINDOW_SECONDS = 60

LIMIT_MESSAGES = {
    "number": (
        "You reached today's message limit for this trial. "
        "You can continue tomorrow."
    ),
    "total": (
        "The trial agent has used all of today's available capacity. "
        "It will be available again tomorrow."
    ),
}

_recent_messages = defaultdict(deque)
_minute_lock = threading.Lock()
_daily_lock = threading.Lock()

_daily_limit = os.getenv("DAILY_LIMIT")
DAILY_LIMIT = int(_daily_limit) if _daily_limit is not None else None
_daily_limit_total = os.getenv("DAILY_LIMIT_TOTAL")
DAILY_LIMIT_TOTAL = (
    int(_daily_limit_total) if _daily_limit_total is not None else None
)

_daily_count = {
    "day": date.today(),
    "by_number": {},
    "total": 0,
}

BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")


def is_token_valid(token: str | None) -> bool:
    if not BRIDGE_TOKEN or not isinstance(token, str):
        return False

    return hmac.compare_digest(token, BRIDGE_TOKEN)


def is_rate_limit_allowed(client_id: str) -> bool:
    now = time.time()
    with _minute_lock:
        messages = _recent_messages[client_id]
        while messages and messages[0] < now - WINDOW_SECONDS:
            messages.popleft()

        if len(messages) >= MAX_MESSAGES:
            return False

        messages.append(now)
        return True


def _reset_daily_count_if_needed() -> None:
    today = date.today()
    if _daily_count["day"] != today:
        _daily_count["day"] = today
        _daily_count["by_number"] = {}
        _daily_count["total"] = 0


def is_daily_limit_allowed(client_id: str) -> tuple[bool, str | None]:
    with _daily_lock:
        _reset_daily_count_if_needed()
        client_count = _daily_count["by_number"].get(client_id, 0)
        if DAILY_LIMIT is not None and client_count >= DAILY_LIMIT:
            return False, LIMIT_MESSAGES["number"]
        if (
            DAILY_LIMIT_TOTAL is not None
            and _daily_count["total"] >= DAILY_LIMIT_TOTAL
        ):
            return False, LIMIT_MESSAGES["total"]

        _daily_count["by_number"][client_id] = client_count + 1
        _daily_count["total"] += 1
        return True, None
