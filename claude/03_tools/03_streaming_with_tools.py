"""
03 - Streaming with Tools (Fine-Grained Event Stream)

Compares two levels of streaming granularity:

  COARSE      — text_stream only
                Yields text tokens but silently skips all tool events.
                Claude appears to return nothing when it calls a tool.

  FINE-GRAINED — raw SSE events
                Surfaces every event: content_block_start/delta/stop,
                input_json_delta for tool inputs, message_delta for
                stop_reason. Required for a correct streaming tool loop.
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
                "city": {"type": "string", "description": "City name, e.g. 'Tokyo'."},
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
                "expression": {"type": "string", "description": "Math expression, e.g. '12 * 8'."},
            },
            "required": ["expression"],
        },
    },
]


# --- Simulated tool execution ---------------------------------------------------

def run_tool(name: str, inputs: dict) -> str:
    if name == "get_weather":
        city = inputs["city"]
        return json.dumps({"city": city, "temperature": "22°C", "condition": "Partly cloudy"})
    if name == "calculator":
        try:
            result = eval(inputs["expression"], {"__builtins__": {}})
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})
    return json.dumps({"error": f"Unknown tool: {name}"})


# --- APPROACH 1: Coarse streaming (text_stream only) ----------------------------

def stream_coarse(client: anthropic.Anthropic, prompt: str) -> None:
    """
    Uses the high-level text_stream helper.
    Problem: text_stream only yields TextDelta events. When Claude's first
    response is a tool call (no text block), text_stream yields nothing and
    the function silently returns an empty string — the tool never runs.
    """
    print(f"[COARSE] User: {prompt}")
    print("[COARSE] Claude: ", end="", flush=True)

    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        tools=TOOLS,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for token in stream.text_stream:
            print(f"[COARSE] Received token: '{token}'")
            print(token, end="", flush=True)

        stream_final_response = stream.get_final_message()

    print(f"\n[COARSE] Final response content: {stream_final_response}")
    print(f"[COARSE] stop_reason='{stream_final_response.stop_reason}' "
          f"— {'tool call was silently dropped!' if stream_final_response.stop_reason == 'tool_use' else 'ok'}\n")

# --- APPROACH 2: Fine-grained streaming (raw SSE events) -----------------------

def stream_fine_grained(client: anthropic.Anthropic, prompt: str) -> None:
    """
    Iterates over raw SSE events to handle both text tokens and tool calls.

    Event sequence for a tool call:
      RawContentBlockStartEvent  (type='tool_use', has id + name)
      RawContentBlockDeltaEvent  (type='input_json_delta', streams partial JSON)
      RawContentBlockDeltaEvent  ...
      RawContentBlockStopEvent
      RawMessageDeltaEvent       (stop_reason='tool_use')

    Event sequence for plain text:
      RawContentBlockStartEvent  (type='text')
      RawContentBlockDeltaEvent  (type='text_delta', streams tokens)
      RawContentBlockDeltaEvent  ...
      RawContentBlockStopEvent
      RawMessageDeltaEvent       (stop_reason='end_turn')
    """
    print(f"[FINE-GRAINED] User: {prompt}")
    messages = [{"role": "user", "content": prompt}]

    while True:
        # State accumulated from the raw event stream for this one API call.
        current_block_type = None          # 'text' or 'tool_use'
        current_tool_id = None
        current_tool_name = None
        current_tool_input_chunks: list[str] = []
        completed_tool_uses: list[dict] = []
        response_content_blocks = []       # full content list for message history
        stop_reason = None

        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            for event in stream:           # iterate raw SSE events
                # Use event.type (stable API string) not type(event).__name__ (fragile class name).
                etype = event.type

                #print(f"*** [FINE-GRAINED] ReceivedEventType='{etype}'  ReceivedEvent={event}")

                # -- A new content block is starting --------------------------------
                if etype == "content_block_start":
                    block = event.content_block
                    current_block_type = block.type

                    if block.type == "text":
                        print("[FINE-GRAINED] Claude (streaming text): ", end="", flush=True)
                        response_content_blocks.append({"type": "text", "text": ""})

                    elif block.type == "tool_use":
                        current_tool_id = block.id
                        current_tool_name = block.name
                        current_tool_input_chunks = []
                        print(f"\n[FINE-GRAINED] Tool call starting: {block.name} "
                              f"(id={block.id})")
                        print("[FINE-GRAINED] Streaming tool input JSON: ", end="", flush=True)
                        response_content_blocks.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": {},    # filled in at block stop
                        })

                # -- Incremental data arriving for the current block ----------------
                elif etype == "content_block_delta":
                    delta = event.delta

                    if delta.type == "text_delta":
                        print(delta.text, end="", flush=True)
                        response_content_blocks[-1]["text"] += delta.text

                    elif delta.type == "input_json_delta":
                        # Tool input arrives as partial JSON fragments.
                        print(delta.partial_json, end="", flush=True)
                        current_tool_input_chunks.append(delta.partial_json)

                # -- A content block has finished -----------------------------------
                elif etype == "content_block_stop":
                    print()   # newline after streamed content

                    if current_block_type == "tool_use":
                        full_json = "".join(current_tool_input_chunks)
                        parsed_input = json.loads(full_json) if full_json else {}
                        # Patch the placeholder we added at block start.
                        response_content_blocks[-1]["input"] = parsed_input
                        completed_tool_uses.append({
                            "id": current_tool_id,
                            "name": current_tool_name,
                            "input": parsed_input,
                        })
                    current_block_type = None

                # -- Final message metadata -----------------------------------------
                elif etype == "message_delta":
                    stop_reason = event.delta.stop_reason
                    print(f"[FINE-GRAINED] stop_reason='{stop_reason}'")

        # Append Claude's full response to history so tool results have context.
        messages.append({"role": "assistant", "content": response_content_blocks})

        if stop_reason == "end_turn":
            break

        if stop_reason == "tool_use":
            tool_results = []
            for tool_use in completed_tool_uses:
                result = run_tool(tool_use["name"], tool_use["input"])
                print(f"[FINE-GRAINED] Executed {tool_use['name']}({tool_use['input']}) → {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use["id"],
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})
            print("[FINE-GRAINED] Sending tool results back, continuing stream...\n")

    print()


# --- Entry point ----------------------------------------------------------------

if __name__ == "__main__":
    client = anthropic.Anthropic()

    prompt = "What's the weather in Tokyo and what is 128 * 4?"

    print("=" * 60)
    print("APPROACH 1 — COARSE (text_stream only)")
    print("=" * 60)
    stream_coarse(client, prompt)

    print("=" * 60)
    print("APPROACH 2 — FINE-GRAINED (raw SSE events)")
    print("=" * 60)
    stream_fine_grained(client, prompt)