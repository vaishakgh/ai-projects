"""
01 - Single-Turn Conversation with Tools
Defines tools, sends one user message, handles a tool call if Claude makes one,
then returns the final text response.
"""

import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"

# --- Tool definitions -----------------------------------------------------------

TOOLS = [
    {
        "name": "get_weather",
        "description": "Returns the current weather for a given city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name, e.g. 'San Francisco'.",
                },
            },
            "required": ["city"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluates a basic arithmetic expression and returns the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression, e.g. '12 * 8 + 5'.",
                },
            },
            "required": ["expression"],
        },
    },
]


# --- Simulated tool execution ---------------------------------------------------

def run_tool(name: str, inputs: dict) -> str:
    """Execute a tool locally and return a string result."""
    if name == "get_weather":
        # Simulated response — replace with a real API call if desired.
        city = inputs["city"]
        return json.dumps({"city": city, "temperature": "22°C", "condition": "Partly cloudy"})

    if name == "calculator":
        try:
            # eval is safe here because we control the expression source (Claude's structured output).
            result = eval(inputs["expression"], {"__builtins__": {}})
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})

    return json.dumps({"error": f"Unknown tool: {name}"})


# --- Single-turn helper ---------------------------------------------------------

def ask_with_tools(client: anthropic.Anthropic, user_prompt: str) -> str:
    """
    Send one user message. If Claude requests a tool, execute it and send the
    result back, then return the final text reply.
    """
    messages = [{"role": "user", "content": user_prompt}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=TOOLS,
        messages=messages,
    )

    # Claude may respond with text, a tool_use block, or both.
    # Keep looping until stop_reason is "end_turn" (no more tool calls).
    while response.stop_reason == "tool_use":
        # Collect all tool_use blocks from this response.
        tool_uses = [block for block in response.content if block.type == "tool_use"]

        # Append Claude's full response (may include text + tool_use blocks) to history.
        messages.append({"role": "assistant", "content": response.content})

        # Build one tool_result block per tool call.
        tool_results = []
        for tool_use in tool_uses:
            print(f"  [tool call] {tool_use.name}({tool_use.input})")
            result = run_tool(tool_use.name, tool_use.input)
            print(f"  [tool result] {result}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        # Send all tool results back in a single user turn.
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

    return next(block.text for block in response.content if block.type == "text")


# --- Entry point ----------------------------------------------------------------

if __name__ == "__main__":
    client = anthropic.Anthropic()

    prompts = [
        "What's the weather like in Tokyo right now?",
        "What is 347 * 19?",
    ]

    for prompt in prompts:
        print(f"User  : {prompt}")
        reply = ask_with_tools(client, prompt)
        print(f"Claude: {reply}\n")
