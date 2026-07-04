"""
05 - Web Search Tool
Demonstrates Claude's built-in web search tool.

Key difference from custom tools and text_editor:
  Custom tools  — you define the schema AND implement execution.
  text_editor   — built-in schema, you implement execution (file I/O).
  web_search    — built-in schema, Anthropic executes the search server-side.
                  No execution code needed — one API call returns a complete answer.

Tool configuration options (added directly to the tool definition dict):
  max_uses        — max number of searches Claude can make per request.
                    Useful for controlling cost and latency.
  allowed_domains — allowlist of domains Claude may search.
                    If set, results from all other domains are excluded.
  blocked_domains — blocklist of domains Claude may not search.
                    Cannot be combined with allowed_domains.

Response content blocks produced by a web search:
  server_tool_use        — shows the query Claude sent to the search engine
  web_search_tool_result — shows the raw search results Claude received
  text                   — Claude's final answer
"""

import anthropic
from dotenv import load_dotenv

load_dotenv()

# web_search_20250305 is supported by claude-sonnet-4-6.
# Use web_search_20260209 if available for newer models.
MODEL = "claude-sonnet-4-6"

# --- Tool config ----------------------------------------------------------------
# Adjust these to control how Claude searches.

# Maximum web searches Claude may perform per API request.
# None = no limit imposed by the caller.
MAX_USES = 3

# Only return results from these domains. Set to None to search all domains.
# Cannot be used together with BLOCKED_DOMAINS.
ALLOWED_DOMAINS = ["python.org", "docs.python.org", "pypi.org"]

# Domains to always exclude. Set to None when using ALLOWED_DOMAINS.
BLOCKED_DOMAINS = None

# ---------------------------------------------------------------------------------

def build_tool(
    max_uses: int | None = None,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> dict:
    """
    Build a web search tool definition with optional config fields.
    Only non-None values are included so the API receives a clean dict.
    """
    tool = {
        "type": "web_search_20250305",
        "name": "web_search",
    }
    if max_uses is not None:
        tool["max_uses"] = max_uses
    if allowed_domains is not None:
        tool["allowed_domains"] = allowed_domains
    if blocked_domains is not None:
        tool["blocked_domains"] = blocked_domains
    return tool


# --- Response parser ------------------------------------------------------------

def print_response(response: anthropic.types.Message) -> None:
    """Print each content block in the response with its type labelled."""
    for block in response.content:
        btype = block.type

        if btype == "text":
            print(f"Claude: {block.text}")

        elif btype == "server_tool_use":
            # Claude's outgoing search query (executed server-side by Anthropic).
            query = block.input.get("query", "") if hasattr(block, "input") else ""
            print(f"  [web search] query='{query}'")

        elif btype == "web_search_tool_result":
            # Raw search results returned to Claude (list of result dicts).
            results = block.content if hasattr(block, "content") else []
            print(f"  [search results] {len(results)} result(s) returned")
            for r in results[:3]:            # show first 3 for brevity
                title = getattr(r, "title", "") or r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "")
                url   = getattr(r, "url",   "") or r.get("url",   "") if isinstance(r, dict) else getattr(r, "url",   "")
                print(f"    • {title}  ({url})")

        else:
            # Catch any other block types (e.g. thinking, tool_use) for visibility.
            print(f"  [block type='{btype}']  {str(block)[:120]}")

    print(
        f"\n[stop_reason='{response.stop_reason}'  "
        f"input_tokens={response.usage.input_tokens}  "
        f"output_tokens={response.usage.output_tokens}]\n"
    )


# --- Single-question helper -----------------------------------------------------

def ask(client: anthropic.Anthropic, question: str, tool: dict) -> None:
    """Send one question. Claude searches the web and answers in a single API call."""
    print(f"Question: {question}\n")
    print(f"Tool config: {tool}\n")

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[tool],
        messages=[{"role": "user", "content": question}],
    )

    print_response(response)


# --- Multi-turn helper ----------------------------------------------------------

def chat_with_search(client: anthropic.Anthropic, turns: list[str], tool: dict) -> None:
    """
    Multi-turn conversation where Claude can search on any turn.
    Because web search is server-side, each turn is still a single API call —
    no tool execution loop is needed.
    """
    messages = []

    for question in turns:
        print(f"User  : {question}\n")
        messages.append({"role": "user", "content": question})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=[tool],
            messages=messages,
        )

        print_response(response)

        # Keep Claude's reply in history for context on the next turn.
        # Store only the text blocks to avoid re-sending search result blocks.
        reply_text = " ".join(
            block.text for block in response.content if block.type == "text"
        )
        messages.append({"role": "assistant", "content": reply_text})


# --- Entry point ----------------------------------------------------------------

if __name__ == "__main__":
    client = anthropic.Anthropic()

    # --- Demo 1: allowed_domains only -------------------------------------------
    # Claude may only pull results from python.org and related domains.
    print("=" * 60)
    print("DEMO 1 — allowed_domains (python.org only)")
    print("=" * 60)
    tool_restricted = build_tool(
        max_uses=MAX_USES,
        allowed_domains=ALLOWED_DOMAINS,
    )
    ask(
        client,
        "What is the latest stable version of Python and what are its key new features?",
        tool=tool_restricted,
    )

    # --- Demo 2: no domain restriction, max_uses cap ----------------------------
    # Claude can search anywhere but is capped at 2 searches for this request.
    print("=" * 60)
    print("DEMO 2 — no domain restriction, max_uses=2")
    print("=" * 60)
    tool_capped = build_tool(max_uses=2)
    ask(
        client,
        "What is the current price of Bitcoin in USD?",
        tool=tool_capped,
    )

    # --- Demo 3: multi-turn with config -----------------------------------------
    # Follow-up question that references context from the first turn.
    print("=" * 60)
    print("DEMO 3 — multi-turn with max_uses=3, no domain restriction")
    print("=" * 60)
    tool_default = build_tool(max_uses=3)
    chat_with_search(
        client,
        turns=[
            "Who won the most recent FIFA World Cup?",
            "Which players were the top scorers in that tournament?",
        ],
        tool=tool_default,
    )
