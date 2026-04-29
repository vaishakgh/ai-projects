"""
03 - Multi-Turn Conversation
The API is stateless, so the full message history is sent on every request.
This module wraps that pattern in a simple Conversation class.
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


class Conversation:
    """Manages a stateful multi-turn conversation with Claude."""

    # The Conversation class maintains a message history and an optional system prompt.
    def __init__(
        self,
        client: anthropic.Anthropic,
        system_prompt: str = None,
    ) -> None:
        self._client = client
        self._system_prompt = system_prompt
        self._messages: list[dict] = []

    def send(self, user_message: str) -> str:
        """Append a user turn, call the API, and return the assistant reply."""

        # Appends the new user message to the conversation history as a list.
        self._messages.append({"role": "user", "content": user_message})

        # Builds the API request kwargs, including the full message history and optional system prompt.
        kwargs: dict = dict(
            model=MODEL,
            max_tokens=1024,
            messages=self._messages,
        )
        if self._system_prompt:
            kwargs["system"] = self._system_prompt

        # **kwargs unpacks the dictionary and passes each key-value pair as a named argument.
        response = self._client.messages.create(**kwargs)

        reply = next(block.text for block in response.content if block.type == "text")

        # Appends the assistant's reply to the conversation history, so it will be included in the next turn.
        self._messages.append({"role": "assistant", "content": reply})
        return reply


if __name__ == "__main__":
    client = anthropic.Anthropic()

    # Start a conversation with an optional system prompt to set the assistant's behavior.
    convo = Conversation(client, system_prompt="You are a concise, friendly assistant.")

    turns = [
        "Hi! My name is Alex.",
        "What is my name?",
        "What career would you recommend for someone named Alex who loves Python?",
    ]

    for user_prompt in turns:
        print(f"User  : {user_prompt}")
        reply = convo.send(user_prompt)
        print(f"Claude: {reply}\n")
