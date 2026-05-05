"""
02 - Multi-Turn Conversation with Tools
Wraps the tool-calling loop inside a Conversation class so tools work
seamlessly across multiple user turns.
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
                    "description": "The city name, e.g. 'London'.",
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
                    "description": "A math expression, e.g. '100 / 4'.",
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
        city = inputs["city"]
        return json.dumps({"city": city, "temperature": "18°C", "condition": "Sunny"})

    if name == "calculator":
        try:
            result = eval(inputs["expression"], {"__builtins__": {}})
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})

    return json.dumps({"error": f"Unknown tool: {name}"})


# --- Conversation class ---------------------------------------------------------

class ToolConversation:
    """Multi-turn conversation that transparently handles tool calls."""

    def __init__(self, client: anthropic.Anthropic, system_prompt: str = None) -> None:
        self._client = client
        self._system_prompt = system_prompt
        self._messages: list[dict] = []

    def send(self, user_message: str) -> str:
        """Append a user turn, resolve any tool calls, and return the final reply."""
        self._messages.append({"role": "user", "content": user_message})

        kwargs = dict(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=self._messages,
        )
        if self._system_prompt:
            kwargs["system"] = self._system_prompt

        response = self._client.messages.create(**kwargs)

        # Resolve tool calls before returning to the caller.
        while response.stop_reason == "tool_use":
            tool_uses = [block for block in response.content if block.type == "tool_use"]

            # Store Claude's response (including tool_use blocks) in history.
            self._messages.append({"role": "assistant", "content": response.content})

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

            self._messages.append({"role": "user", "content": tool_results})

            kwargs["messages"] = self._messages
            response = self._client.messages.create(**kwargs)

        reply = next(block.text for block in response.content if block.type == "text")

        # Store the final text reply so future turns have full context.
        self._messages.append({"role": "assistant", "content": reply})
        return reply


# --- Entry point ----------------------------------------------------------------

if __name__ == "__main__":
    client = anthropic.Anthropic()

    convo = ToolConversation(
        client,
        system_prompt="You are a helpful assistant with access to weather and calculator tools.",
    )

    turns = [
        "What's the weather in Paris?",
        "Is that warmer or colder than London?",
        "If I visit both cities and spend 3 days in each, how many days is that in total?",
    ]

    for user_message in turns:
        print(f"User  : {user_message}")
        reply = convo.send(user_message)
        print(f"Claude: {reply}\n")
