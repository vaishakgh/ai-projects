"""
05 - Extended Thinking (Adaptive)
Enables adaptive thinking so Claude decides how much reasoning to apply.
Best used for complex, multi-step problems.
Note: budget_tokens is deprecated on claude-opus-4-6; use adaptive instead.
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


def think(client: anthropic.Anthropic, prompt: str) -> str:
    """Send a prompt with adaptive thinking and return the final response text."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts: list[str] = []

    for block in response.content:
        if block.type == "thinking":
            print("[Internal thinking]")
            print(block.thinking)
            print()
        elif block.type == "text":
            text_parts.append(block.text)

    return "\n".join(text_parts)


if __name__ == "__main__":
    client = anthropic.Anthropic()

    prompt = (
        "I have three boxes. Box A has 4 red balls and 2 blue balls. "
        "Box B has 3 red balls and 5 blue balls. "
        "Box C has 1 red ball and 7 blue balls. "
        "I pick a box at random and draw one ball — it is red. "
        "What is the probability that I picked Box A? Show your working."
    )

    print(f"User: {prompt}\n")
    answer = think(client, prompt)
    print(f"Claude:\n{answer}")
