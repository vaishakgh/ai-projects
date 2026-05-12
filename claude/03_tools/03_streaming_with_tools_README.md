# 03 - Streaming with Tools

Demonstrates the difference between **coarse** and **fine-grained** streaming when tool calls are involved.

---

## The Core Problem

`text_stream` only surfaces `TextDelta` events. When Claude's first response is a tool call (no text block), `text_stream` produces **no output** and the tool **never runs**. Fine-grained streaming over raw SSE events is required to correctly handle tool calls in a streaming loop.

---

## Approaches

| | Approach | How it works | Handles tool calls? |
|---|---|---|---|
| 1 | **Coarse** | `stream.text_stream` | No — silently drops them |
| 2 | **Fine-grained** | `for event in stream` (raw SSE) | Yes — sees every event |

---

## Raw SSE Event Types

Use `event.type` (the stable API string) — not `type(event).__name__` (fragile Python class name that varies across SDK versions).

| `event.type` | Carries | Used for |
|---|---|---|
| `message_start` | message id, model | Stream has started |
| `content_block_start` | block type (`text` / `tool_use`), tool id + name | Know what kind of block is coming |
| `content_block_delta` | `text_delta` or `input_json_delta` | Print token / accumulate tool JSON |
| `content_block_stop` | — | Parse accumulated tool JSON, mark block done |
| `message_delta` | `stop_reason` | Decide whether to run tools and loop |
| `message_stop` | — | Stream fully closed |

---

## Sample Log Output — Prompt: `"What's the weather in Tokyo and what is 128 * 4?"`

### Approach 1 — COARSE

```
[COARSE] User: What's the weather in Tokyo and what is 128 * 4?
[COARSE] Claude:
[COARSE] Final response content: Message(
  content=[ToolUseBlock(..., name='get_weather'), ToolUseBlock(..., name='calculator')],
  stop_reason='tool_use')
[COARSE] stop_reason='tool_use' — tool call was silently dropped!
```

No tokens were printed. Claude called both tools but `text_stream` saw nothing and returned — the tools never ran.

---

### Approach 2 — FINE-GRAINED

#### Turn 1 — Claude responds with two parallel tool calls (streaming their JSON inputs)

```
[FINE-GRAINED] User: What's the weather in Tokyo and what is 128 * 4?

*** [FINE-GRAINED] ReceivedEventType='message_start'  ReceivedEvent=...
*** [FINE-GRAINED] ReceivedEventType='content_block_start'  ReceivedEvent=...

[FINE-GRAINED] Tool call starting: get_weather (id=toolu_01Xxx...)
[FINE-GRAINED] Streaming tool input JSON: {"city": "Tokyo"}

*** [FINE-GRAINED] ReceivedEventType='content_block_stop'  ReceivedEvent=...

*** [FINE-GRAINED] ReceivedEventType='content_block_start'  ReceivedEvent=...

[FINE-GRAINED] Tool call starting: calculator (id=toolu_01Yyy...)
[FINE-GRAINED] Streaming tool input JSON: {"expression": "128 * 4"}

*** [FINE-GRAINED] ReceivedEventType='content_block_stop'  ReceivedEvent=...
*** [FINE-GRAINED] ReceivedEventType='message_delta'  ReceivedEvent=...

[FINE-GRAINED] stop_reason='tool_use'
```

#### Tool execution

```
[FINE-GRAINED] Executed get_weather({'city': 'Tokyo'}) → {"city": "Tokyo", "temperature": "22°C", "condition": "Partly cloudy"}
[FINE-GRAINED] Executed calculator({'expression': '128 * 4'}) → {"result": 512}
[FINE-GRAINED] Sending tool results back, continuing stream...
```

#### Turn 2 — Claude streams the final text reply

```
*** [FINE-GRAINED] ReceivedEventType='content_block_start'  ReceivedEvent=...

[FINE-GRAINED] Claude (streaming text): Here are the results!

🌤️ **Weather in Tokyo:** 22°C, Partly cloudy
🧮 **128 × 4 = 512**

*** [FINE-GRAINED] ReceivedEventType='content_block_stop'  ReceivedEvent=...
*** [FINE-GRAINED] ReceivedEventType='message_delta'  ReceivedEvent=...

[FINE-GRAINED] stop_reason='end_turn'
```

---

## Key Code Sections

| Lines | What it does |
|---|---|
| 85–87 | Coarse: iterates `text_stream` — misses tool events entirely |
| 134 | Fine-grained: `for event in stream` — iterates all raw SSE events |
| 136 | `etype = event.type` — reads the stable API string, not the class name |
| 141–161 | `content_block_start` — detects text vs tool_use block, sets up state |
| 164–174 | `content_block_delta` — prints text token or accumulates `input_json_delta` |
| 177–191 | `content_block_stop` — parses full tool JSON, adds to `completed_tool_uses`, resets block state |
| 193–195 | `message_delta` — captures `stop_reason` to decide next action |
| 203–214 | Executes tools and appends results as a new `user` turn, then loops |

---

## Why `input_json_delta` Streams as Fragments

Tool input JSON arrives as partial chunks because Claude generates it token-by-token like text. Each `input_json_delta` is a fragment of valid JSON that must be concatenated before parsing:

```
Chunk 1: '{"city":'
Chunk 2: ' "To'
Chunk 3: 'kyo"}'
→ Joined: '{"city": "Tokyo"}' → json.loads → {'city': 'Tokyo'}
```

This is why `current_tool_input_chunks` accumulates the fragments and `json.loads` only runs at `content_block_stop`.

---

## Full Log Output — Prompt: `"What's the weather in Tokyo and what is 128 * 4?"`

### Approach 1 — COARSE (`text_stream` only)

`text_stream` printed the initial text but silently dropped both tool calls — the tools never ran.

```
[COARSE] User: What's the weather in Tokyo and what is 128 * 4?
[COARSE] Claude: [COARSE] Received token: 'I\'ll look'
I\'ll look[COARSE] Received token: ' up both at the same time!'
 up both at the same time!

[COARSE] Final response content: ParsedMessage(
  content=[
    ParsedTextBlock(text="I\'ll look up both at the same time!"),
    ToolUseBlock(id='toolu_01UAi...', input={'city': 'Tokyo'}, name='get_weather'),
    ToolUseBlock(id='toolu_01C62...', input={'expression': '128 * 4'}, name='calculator')
  ],
  stop_reason='tool_use')

[COARSE] stop_reason='tool_use' — tool call was silently dropped!
```

---

### Approach 2 — FINE-GRAINED (with debug output)

> **Note on `text` / `input_json` events:** The SDK emits two parallel event streams when iterating `stream`. Alongside the raw `content_block_delta` events, the SDK also fires higher-level `TextEvent` (`event.type='text'`) and `InputJsonEvent` (`event.type='input_json'`) events. These carry the same data as `text_delta` / `input_json_delta` respectively. The code only handles the raw `content_block_*` events; the higher-level ones fall through unhandled.

#### Turn 1 — `message_start`

```
*** [FINE-GRAINED] ReceivedEventType='message_start'
    RawMessageStartEvent(message=Message(id='msg_01Riph...', content=[], stop_reason=None,
      usage=Usage(input_tokens=668, output_tokens=3)), type='message_start')
```

#### Turn 1 — `content_block_start` → `content_block_stop` : Text block (index=0)

```
*** [FINE-GRAINED] ReceivedEventType='content_block_start'
    RawContentBlockStartEvent(content_block=TextBlock(text='', type='text'), index=0)
[FINE-GRAINED] Claude (streaming text):
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=TextDelta(text="I\'ll look", type='text_delta')  →  I\'ll look
*** [FINE-GRAINED] ReceivedEventType='text'   # SDK high-level TextEvent (not handled by our code)
    TextEvent(text="I\'ll look", snapshot="I\'ll look")
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=TextDelta(text=' up the weather in Tokyo and calculate 128 * 4 at the same time!')
*** [FINE-GRAINED] ReceivedEventType='text'   # SDK high-level TextEvent (not handled by our code)
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'
    ParsedContentBlockStopEvent(content_block=ParsedTextBlock(
      text="I\'ll look up the weather in Tokyo and calculate 128 * 4 at the same time!"))
```

#### Turn 1 — `content_block_start` → `content_block_stop` : Tool `get_weather` (index=1)

```
*** [FINE-GRAINED] ReceivedEventType='content_block_start'
    content_block=ToolUseBlock(id='toolu_01YaB3...', input={}, name='get_weather'), index=1
[FINE-GRAINED] Tool call starting: get_weather (id=toolu_01YaB3zUGJEXfKR4b58LzLSq)
[FINE-GRAINED] Streaming tool input JSON:
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='')          # empty first fragment
*** [FINE-GRAINED] ReceivedEventType='input_json'  # SDK high-level InputJsonEvent (not handled)
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='{"c')  →  {"c
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='ity": "T')  →  ity": "T
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='okyo"}')  →  okyo"}
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'
    content_block=ToolUseBlock(input={'city': 'Tokyo'}, name='get_weather')
```

#### Turn 1 — `content_block_start` → `content_block_stop` : Tool `calculator` (index=2)

```
*** [FINE-GRAINED] ReceivedEventType='content_block_start'
    content_block=ToolUseBlock(id='toolu_01UvBk...', input={}, name='calculator'), index=2
[FINE-GRAINED] Tool call starting: calculator (id=toolu_01UvBkVXstqNF7G1diw16Umw)
[FINE-GRAINED] Streaming tool input JSON:
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='{"expres')  →  {"expres
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='sion": "12')  →  sion": "12
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='8 ')  →  8
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    delta=InputJSONDelta(partial_json='* 4"}')  →  * 4"}
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'
    content_block=ToolUseBlock(input={'expression': '128 * 4'}, name='calculator')
```

#### Turn 1 — `message_delta` and `message_stop`

```
*** [FINE-GRAINED] ReceivedEventType='message_delta'
    delta=Delta(stop_reason='tool_use')  usage=MessageDeltaUsage(input_tokens=668, output_tokens=114)
[FINE-GRAINED] stop_reason='tool_use'

*** [FINE-GRAINED] ReceivedEventType='message_stop'
    ParsedMessageStopEvent(message=ParsedMessage(
      content=[TextBlock(...), ToolUseBlock(name='get_weather'), ToolUseBlock(name='calculator')],
      stop_reason='tool_use'))
```

#### Tool execution (between Turn 1 and Turn 2)

```
[FINE-GRAINED] Executed get_weather({'city': 'Tokyo'}) → {"city": "Tokyo", "temperature": "22°C", "condition": "Partly cloudy"}
[FINE-GRAINED] Executed calculator({'expression': '128 * 4'}) → {"result": 512}
[FINE-GRAINED] Sending tool results back, continuing stream...
```

#### Turn 2 — `message_start` → text → `message_stop`

```
*** [FINE-GRAINED] ReceivedEventType='message_start'
    Message(id='msg_011kUf...', stop_reason=None, usage=Usage(input_tokens=875, output_tokens=1))

*** [FINE-GRAINED] ReceivedEventType='content_block_start'
    content_block=TextBlock(text='', type='text'), index=0
[FINE-GRAINED] Claude (streaming text):
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  TextDelta(text='Here')  →  Here
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    TextDelta(text=' are your answers:\n\n- 🌤️ **Weather in Tokyo:** It')
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    TextDelta(text="\'s currently **22°C** and **partly cloudy**.\n- 🧮 **128 × 4 = 512**")
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'
    TextDelta(text='\n\nLet me know if you need anything else!')
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'
    ParsedTextBlock(text="Here are your answers:\n\n- 🌤️ **Weather in Tokyo:** It\'s currently **22°C** ...")

*** [FINE-GRAINED] ReceivedEventType='message_delta'
    delta=Delta(stop_reason='end_turn')  usage=MessageDeltaUsage(input_tokens=875, output_tokens=63)
[FINE-GRAINED] stop_reason='end_turn'

*** [FINE-GRAINED] ReceivedEventType='message_stop'
    ParsedMessageStopEvent(message=ParsedMessage(stop_reason='end_turn', ...))
```

---

### Approach 2 — FINE-GRAINED (clean output, no debug lines)

```
[FINE-GRAINED] User: What\'s the weather in Tokyo and what is 128 * 4?
[FINE-GRAINED] Claude (streaming text): I\'ll look up both at the same time!

[FINE-GRAINED] Tool call starting: get_weather (id=toolu_013LEQ...)
[FINE-GRAINED] Streaming tool input JSON: {"city": "Tokyo"}

[FINE-GRAINED] Tool call starting: calculator (id=toolu_013SMD...)
[FINE-GRAINED] Streaming tool input JSON: {"expression": "128 * 4"}
[FINE-GRAINED] stop_reason=\'tool_use\'
[FINE-GRAINED] Executed get_weather({\'city\': \'Tokyo\'}) → {"city": "Tokyo", "temperature": "22°C", "condition": "Partly cloudy"}
[FINE-GRAINED] Executed calculator({\'expression\': \'128 * 4\'}) → {"result": 512}
[FINE-GRAINED] Sending tool results back, continuing stream...

[FINE-GRAINED] Claude (streaming text): Here are your answers:

- 🌤️ **Weather in Tokyo:** It\'s currently **22°C** and **partly cloudy**.
- 🔢 **128 × 4 = 512**

Let me know if you need anything else!
[FINE-GRAINED] stop_reason=\'end_turn\'
```
