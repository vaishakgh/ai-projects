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

    claude_response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=TOOLS,
        messages=messages,
    )

    print(f"Claude Initial response: {claude_response}")

    # Claude may respond with text, a tool_use block, or both.
    # Keep looping until stop_reason is "end_turn" (no more tool calls).
    while claude_response.stop_reason == "tool_use":
        # Collect all tool_use blocks from this response.
        tool_uses = [block for block in claude_response.content if block.type == "tool_use"]

        # Append Claude's full response (may include text + tool_use blocks) to history.
        messages.append({"role": "assistant", "content": claude_response.content})

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

        claude_response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        print(f"Claude Final response: {claude_response}")

    return next(block.text for block in claude_response.content if block.type == "text")


# --- Entry point ----------------------------------------------------------------

if __name__ == "__main__":
    client = anthropic.Anthropic()

    prompts = [
        "What's the weather like in Tokyo right now?",
        "What is 347 * 19?",
    #    "What is the weather now in China?",
    #    "What is the weather now in New York? Add 345 and 567 together for me as well, please.",
    ]

    for prompt in prompts:
        print(f"User  : {prompt}")
        reply = ask_with_tools(client, prompt)
        print(f"Claude: {reply}\n")





"""
Log output from running the above code:

User  : What's the weather like in Tokyo right now?
Claude Initial response: Message(id='msg_01AvGcMaPyEdLKhsobTwZgks', container=None, 
content=[ToolUseBlock(id='toolu_01NpShALcjYz4wms3xrUYRc5', caller=DirectCaller(type='direct'), input={'city': 'Tokyo'}, name='get_weather', type='tool_use')], 
model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=669, output_tokens=54, server_tool_use=None, service_tier='standard'))
  [tool call] get_weather({'city': 'Tokyo'})
  [tool result] {"city": "Tokyo", "temperature": "22\u00b0C", "condition": "Partly cloudy"}
Claude Final response: Message(id='msg_018Q76hnK4KWCTXrrNZ2D9Ha', container=None, 
content=[TextBlock(citations=None, text='The current weather in **Tokyo** is **22°C** and **partly cloudy**. It sounds like a mild and pleasant day! 🌤️ Let me know if you need any other information.', type='text')], 
model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=762, output_tokens=48, server_tool_use=None, service_tier='standard'))
Claude: The current weather in **Tokyo** is **22°C** and **partly cloudy**. It sounds like a mild and pleasant day! 🌤️ Let me know if you need any other information.

User  : What is 347 * 19?
Claude Initial response: Message(id='msg_01EhmRz4QsFc52eJbsvJmZKz', container=None, 
content=[ToolUseBlock(id='toolu_01HFHUJGm7PAmtoh7imhiAg1', caller=DirectCaller(type='direct'), input={'expression': '347 * 19'}, name='calculator', type='tool_use')], 
model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=668, output_tokens=56, server_tool_use=None, service_tier='standard'))
  [tool call] calculator({'expression': '347 * 19'})
  [tool result] {"result": 6593}
Claude Final response: Message(id='msg_01Egu1kBRM1MiDsPBz1QQN2W', container=None, 
content=[TextBlock(citations=None, text='The result of **347 × 19 = 6,593**.', type='text')], 
model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=742, output_tokens=19, server_tool_use=None, service_tier='standard'))
Claude: The result of **347 × 19 = 6,593**.



User  : What is the weather now in China?
Claude Initial response: Message(id='msg_01VpPXKhs9Ak9B4i32gpmH9X', container=None, content=[TextBlock(citations=None, text="China is a vast country with many cities, each potentially having different weather conditions. Could you please specify which **city in China** you'd like to know the weather for? For example:\n\n- **Beijing**\n- **Shanghai**\n- **Guangzhou**\n- **Shenzhen**\n- **Chengdu**", type='text')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=667, output_tokens=74, server_tool_use=None, service_tier='standard'))
Claude: China is a vast country with many cities, each potentially having different weather conditions. Could you please specify which **city in China** you'd like to know the weather for? For example:

- **Beijing**
- **Shanghai**
- **Guangzhou**
- **Shenzhen**
- **Chengdu**

User  : What is the weather now in New York? Add 345 and 567 together for me as well, please.
Claude Initial response: Message(id='msg_015tXEA9X3Vmyb5dHL4i6vz9', container=None, 
content=[TextBlock(citations=None, text='Sure! Let me fetch the weather in New York and calculate that sum at the same time!', type='text'), ToolUseBlock(id='toolu_015AH28MNHsbyNAE2tv5Cawv', caller=DirectCaller(type='direct'), input={'city': 'New York'}, name='get_weather', type='tool_use'), 
ToolUseBlock(id='toolu_01Eooje6ppAQGvWvCTY9ED6j', caller=DirectCaller(type='direct'), input={'expression': '345 + 567'}, name='calculator', type='tool_use')], 
model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=684, output_tokens=112, server_tool_use=None, service_tier='standard'))
  [tool call] get_weather({'city': 'New York'})
  [tool result] {"city": "New York", "temperature": "22\u00b0C", "condition": "Partly cloudy"}
  [tool call] calculator({'expression': '345 + 567'})
  [tool result] {"result": 912}
Claude Final response: Message(id='msg_01PeeeWrBNVYT2wKbBfccLPD', container=None, 
content=[TextBlock(citations=None, text="Here are the results!\n\n🌤️ **Weather in New York:**\n- **Temperature:** 22°C\n- **Condition:** Partly Cloudy\n\n🧮 **345 + 567 = 912**\n\nLet me know if there's anything else you'd like to know!", type='text')], 
model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=890, output_tokens=71, server_tool_use=None, service_tier='standard'))
Claude: Here are the results!

🌤️ **Weather in New York:**
- **Temperature:** 22°C
- **Condition:** Partly Cloudy

🧮 **345 + 567 = 912**

Let me know if there's anything else you'd like to know!

"""