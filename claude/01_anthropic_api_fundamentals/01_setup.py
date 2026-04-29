"""
01 - Setup & Authentication
Demonstrates how to initialise the Anthropic client.
The SDK reads ANTHROPIC_API_KEY from the environment automatically.
"""

import os
import anthropic
from dotenv import load_dotenv

load_dotenv()  # loads .env file into environment


def make_client() -> anthropic.Anthropic:
    """Return an authenticated Anthropic client."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. "
            "Export it before running: export ANTHROPIC_API_KEY=sk-ant-..."
        )
    return anthropic.Anthropic(api_key=api_key)


if __name__ == "__main__":
    client = make_client()
    print("Client initialised successfully.")
    print(f"Base URL: {client.base_url}")
