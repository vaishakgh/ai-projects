"""
04 - Streaming Responses
Prints tokens to the terminal as they arrive instead of waiting for the full reply.
Use streaming any time you expect a long response or want low time-to-first-token.
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


def stream(client: anthropic.Anthropic, prompt: str) -> str:
    """Stream a response and return the complete text when done."""
    chunks: list[str] = []

    # The `with` block ensures proper cleanup of the stream context, even if an error occurs.
    # client.messages.stream is for streaming responses. 
    # client.conversations.stream - if you want to stream a conversation.
    # client.messages.create is for single or multi-turn conversations.
    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    ) as stream_ctx:
        for token in stream_ctx.text_stream:
            print(token, end="", flush=True)
            chunks.append(token)

        final = stream_ctx.get_final_message()

    print()  # newline after the streamed output
    print(
        f"\n[Usage] input={final.usage.input_tokens} "
        f"output={final.usage.output_tokens} tokens"
    )

    return "".join(chunks)


if __name__ == "__main__":
    client = anthropic.Anthropic()

    prompt = "Write a short three-sentence story about a robot who learns to bake bread."
    print(f"User: {prompt}\n")
    print("Claude (streaming):\n")

    stream(client, prompt)
