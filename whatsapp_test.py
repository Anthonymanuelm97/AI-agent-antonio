import argparse
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_MESSAGE = "¿Cuánto cuesta un cappuccino?"
DEFAULT_CLIENT_ID = "whatsapp:18095550000"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a test request to the protected WhatsApp endpoint."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--client-id", default=DEFAULT_CLIENT_ID)
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Send the /reset command.",
    )
    parser.add_argument(
        "--oversized",
        action="store_true",
        help="Send a 501-character message to test input validation.",
    )
    token_options = parser.add_mutually_exclusive_group()
    token_options.add_argument(
        "--missing-token",
        action="store_true",
        help="Omit X-Bridge-Token to test authorization.",
    )
    token_options.add_argument(
        "--invalid-token",
        action="store_true",
        help="Send an invalid token to test authorization.",
    )
    arguments = parser.parse_args()
    if arguments.repeat < 1:
        parser.error("--repeat must be at least 1")
    if arguments.reset and arguments.oversized:
        parser.error("--reset and --oversized cannot be used together")
    return arguments


def main() -> None:
    arguments = parse_arguments()
    base_url = arguments.base_url.strip().rstrip("/")
    if not base_url:
        raise SystemExit("API base URL must not be empty.")

    message = "/reset" if arguments.reset else arguments.message
    if arguments.oversized:
        message = "x" * 501

    token = os.getenv("BRIDGE_TOKEN", "").strip()
    headers = {"Content-Type": "application/json"}
    expected_status = 200
    if arguments.invalid_token:
        headers["X-Bridge-Token"] = "invalid-test-token"
        expected_status = 401
    elif arguments.missing_token:
        expected_status = 401
    elif token:
        headers["X-Bridge-Token"] = token
    else:
        raise SystemExit(
            "BRIDGE_TOKEN is not configured. Set it in the project .env file "
            "or use --missing-token to test authorization."
        )

    request_body = {
        "client_id": arguments.client_id,
        "message": message,
    }

    for request_number in range(1, arguments.repeat + 1):
        try:
            response = httpx.post(
                f"{base_url}/whatsapp/chat",
                json=request_body,
                headers=headers,
                timeout=60,
            )
        except httpx.HTTPError as error:
            raise SystemExit(f"WhatsApp API request failed: {error}") from error

        print(f"[{request_number}] HTTP {response.status_code}")
        if response.status_code != expected_status:
            print(response.text)
            raise SystemExit(
                f"Expected HTTP {expected_status}, received "
                f"{response.status_code}."
            )

        if response.status_code == 401:
            print("Authorization rejection verified.")
            continue

        try:
            result = response.json()
        except ValueError as error:
            raise SystemExit("WhatsApp API returned invalid JSON.") from error

        if (
            not isinstance(result, dict)
            or result.get("client_id") != arguments.client_id
            or not isinstance(result.get("response"), str)
        ):
            raise SystemExit(
                "WhatsApp API response must contain the requested client_id "
                "and a string response."
            )

        print(result["response"])


if __name__ == "__main__":
    main()
