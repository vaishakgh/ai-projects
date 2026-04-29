"""
06 - Temperature & System Prompts
Demonstrates how system prompts shape Claude's persona/behaviour,
and how temperature controls response randomness/creativity.

Temperature:
  0.0  — deterministic, focused, consistent (good for factual/code tasks)
  0.5  — balanced (good for general use)
  1.0  — creative, varied, less predictable (good for creative writing)

System prompt:
  Sets Claude's role, tone, constraints, and context before the conversation starts.
  Not visible to the end user — purely for shaping behaviour.
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


def ask_with_persona(
    client: anthropic.Anthropic,
    system: str,
    prompt: str,
    temperature: float = 1.0,
) -> str:
    """Send a message with a custom system prompt and temperature."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(block.text for block in response.content if block.type == "text")


if __name__ == "__main__":
    client = anthropic.Anthropic()

    user_prompt = "Explain what a REST API is."

    examples = [
        {
            "label": "Formal technical expert (temp=0.0)",
            "system": "You are a senior software architect. Give precise, technical answers with no fluff.",
            "temperature": 0.0,
        },
        {
            "label": "Friendly teacher for beginners (temp=0.5)",
            "system": "You are a friendly coding tutor explaining concepts to someone with no programming experience. Use simple language and relatable analogies.",
            "temperature": 0.5,
        },
        {
            "label": "Creative storyteller (temp=1.0)",
            "system": "You are a creative writer. Explain technical concepts through short imaginative stories or metaphors.",
            "temperature": 1.0,
        },
    ]

    for example in examples:
        print(f"--- {example['label']} ---")
        reply = ask_with_persona(
            client,
            system=example["system"],
            prompt=user_prompt,
            temperature=example["temperature"],
        )
        print(reply)
        print()
