"""
02 - Single-Turn Message
Sends one user message and prints the text response.
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


def ask(client: anthropic.Anthropic, user_prompt: str) -> str:
    """Send a single user message and return the response text."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )
    # The response content is a list of blocks, which can be text, images, etc. 
    # Filters for the first text block and returns its text.
    return next(block.text for block in response.content if block.type == "text")


if __name__ == "__main__":
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    user_prompt = "What is the capital of France?"
    print(f"User: {user_prompt}\n")

    answer = ask(client, user_prompt)
    print(f"Claude: {answer}")
