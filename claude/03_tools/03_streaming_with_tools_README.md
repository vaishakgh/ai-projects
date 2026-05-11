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


============================================================
APPROACH 1 — COARSE (text_stream only)
============================================================
[COARSE] User: What's the weather in Tokyo and what is 128 * 4?

[COARSE] Claude: [COARSE] Received token: 'I'll look'
I'll look[COARSE] Received token: ' up both at the same time!'
 up both at the same time!

[COARSE] Final response content: ParsedMessage(id='msg_01MopHbfqU74n87dkgpPywYa', container=None, 
content=[ParsedTextBlock(citations=None, text="I'll look up both at the same time!", type='text', parsed_output=None), 
ToolUseBlock(id='toolu_01UAixH1wMQuCGineiqRiZda', caller=DirectCaller(type='direct'), input={'city': 'Tokyo'}, name='get_weather', type='tool_use'), 
ToolUseBlock(id='toolu_01C62yYq9D2LjCw5tn24vNKK', caller=DirectCaller(type='direct'), input={'expression': '128 * 4'}, name='calculator', type='tool_use')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, 
type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=668, output_tokens=102, server_tool_use=None, service_tier='standard'))

[COARSE] stop_reason='tool_use' — tool call was silently dropped!

========================================================================================================================


#Log with additional log output
============================================================
APPROACH 2 — FINE-GRAINED (raw SSE events)
============================================================
[FINE-GRAINED] User: What's the weather in Tokyo and what is 128 * 4?

# eventType MessageStart : Claude Assistant Message
*** [FINE-GRAINED] ReceivedEventType='message_start'  ReceivedEvent=RawMessageStartEvent(message=Message(id='msg_01RiphQW8wEoYKuRdaNnRFbr', container=None, content=[], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason=None, stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=668, output_tokens=3, server_tool_use=None, service_tier='standard')), type='message_start')

# eventType ContentBlockStart - eventType ContentBlockStop : Text
*** [FINE-GRAINED] ReceivedEventType='content_block_start'  ReceivedEvent=RawContentBlockStartEvent(content_block=TextBlock(citations=None, text='', type='text'), index=0, type='content_block_start')
[FINE-GRAINED] Claude (streaming text): 
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=TextDelta(text="I'll look", type='text_delta'), index=0, type='content_block_delta') I'll look
*** [FINE-GRAINED] ReceivedEventType='text'  ReceivedEvent=TextEvent(type='text', text="I'll look", snapshot="I'll look")
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=TextDelta(text=' up the weather in Tokyo and calculate 128 * 4 at the same time!', type='text_delta'), index=0, type='content_block_delta') up the weather in Tokyo and calculate 128 * 4 at the same time!
 *** [FINE-GRAINED] ReceivedEventType='text'  ReceivedEvent=TextEvent(type='text', text=' up the weather in Tokyo and calculate 128 * 4 at the same time!', snapshot="I'll look up the weather in Tokyo and calculate 128 * 4 at the same time!")
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'  ReceivedEvent=ParsedContentBlockStopEvent(index=0, type='content_block_stop', content_block=ParsedTextBlock(citations=None, text="I'll look up the weather in Tokyo and calculate 128 * 4 at the same time!", type='text', parsed_output=None))


# eventType ContentBlockStart - eventType ContentBlockStop : Tool get_weather
*** [FINE-GRAINED] ReceivedEventType='content_block_start'  ReceivedEvent=RawContentBlockStartEvent(content_block=ToolUseBlock(id='toolu_01YaB3zUGJEXfKR4b58LzLSq', caller=DirectCaller(type='direct'), input={}, name='get_weather', type='tool_use'), index=1, type='content_block_start')
[FINE-GRAINED] Tool call starting: get_weather (id=toolu_01YaB3zUGJEXfKR4b58LzLSq)
[FINE-GRAINED] Streaming tool input JSON: 
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='', type='input_json_delta'), index=1, type='content_block_delta')
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='', snapshot={})
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='{"c', type='input_json_delta'), index=1, type='content_block_delta') {"c
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='{"c', snapshot={})
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='ity": "T', type='input_json_delta'), index=1, type='content_block_delta') ity": "T
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='ity": "T', snapshot={})
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='okyo"}', type='input_json_delta'), index=1, type='content_block_delta') okyo"}
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='okyo"}', snapshot={'city': 'Tokyo'})
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'  ReceivedEvent=ParsedContentBlockStopEvent(index=1, type='content_block_stop', content_block=ToolUseBlock(id='toolu_01YaB3zUGJEXfKR4b58LzLSq', caller=DirectCaller(type='direct'), input={'city': 'Tokyo'}, name='get_weather', type='tool_use'))


# eventType ContentBlockStart - eventType ContentBlockStop : Tool calculator
*** [FINE-GRAINED] ReceivedEventType='content_block_start'  ReceivedEvent=RawContentBlockStartEvent(content_block=ToolUseBlock(id='toolu_01UvBkVXstqNF7G1diw16Umw', caller=DirectCaller(type='direct'), input={}, name='calculator', type='tool_use'), index=2, type='content_block_start')
[FINE-GRAINED] Tool call starting: calculator (id=toolu_01UvBkVXstqNF7G1diw16Umw)
[FINE-GRAINED] Streaming tool input JSON: 
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='', type='input_json_delta'), index=2, type='content_block_delta')
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='', snapshot={})
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='{"expres', type='input_json_delta'), index=2, type='content_block_delta') {"expres
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='{"expres', snapshot={})
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='sion": "12', type='input_json_delta'), index=2, type='content_block_delta') sion": "12
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='sion": "12', snapshot={})
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='8 ', type='input_json_delta'), index=2, type='content_block_delta') 8 
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='8 ', snapshot={})
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=InputJSONDelta(partial_json='* 4"}', type='input_json_delta'), index=2, type='content_block_delta') * 4"}
*** [FINE-GRAINED] ReceivedEventType='input_json'  ReceivedEvent=InputJsonEvent(type='input_json', partial_json='* 4"}', snapshot={'expression': '128 * 4'})
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'  ReceivedEvent=ParsedContentBlockStopEvent(index=2, type='content_block_stop', content_block=ToolUseBlock(id='toolu_01UvBkVXstqNF7G1diw16Umw', caller=DirectCaller(type='direct'), input={'expression': '128 * 4'}, name='calculator', type='tool_use'))


# eventType MessageDelta
*** [FINE-GRAINED] ReceivedEventType='message_delta'  ReceivedEvent=RawMessageDeltaEvent(delta=Delta(container=None, stop_details=None, stop_reason='tool_use', stop_sequence=None), type='message_delta', usage=MessageDeltaUsage(cache_creation_input_tokens=0, cache_read_input_tokens=0, input_tokens=668, output_tokens=114, server_tool_use=None))
[FINE-GRAINED] stop_reason='tool_use'

# eventType MessageStop
*** [FINE-GRAINED] ReceivedEventType='message_stop'  ReceivedEvent=ParsedMessageStopEvent(type='message_stop', message=ParsedMessage(id='msg_01RiphQW8wEoYKuRdaNnRFbr', container=None, content=[ParsedTextBlock(citations=None, text="I'll look up the weather in Tokyo and calculate 128 * 4 at the same time!", type='text', parsed_output=None), ToolUseBlock(id='toolu_01YaB3zUGJEXfKR4b58LzLSq', caller=DirectCaller(type='direct'), input={'city': 'Tokyo'}, name='get_weather', type='tool_use'), 
ToolUseBlock(id='toolu_01UvBkVXstqNF7G1diw16Umw', caller=DirectCaller(type='direct'), input={'expression': '128 * 4'}, name='calculator', type='tool_use')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=668, output_tokens=114, server_tool_use=None, service_tier='standard')))
[FINE-GRAINED] Executed get_weather({'city': 'Tokyo'}) → {"city": "Tokyo", "temperature": "22\u00b0C", "condition": "Partly cloudy"}
[FINE-GRAINED] Executed calculator({'expression': '128 * 4'}) → {"result": 512}
[FINE-GRAINED] Sending tool results back, continuing stream...




# eventType MessageStart
*** [FINE-GRAINED] ReceivedEventType='message_start'  ReceivedEvent=RawMessageStartEvent(message=Message(id='msg_011kUf9zcJSWfN3brsvN8h9i', container=None, content=[], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason=None, stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=875, output_tokens=1, server_tool_use=None, service_tier='standard')), type='message_start')


# eventType ContentBlockStart - eventType ContentBlockStop : Text
*** [FINE-GRAINED] ReceivedEventType='content_block_start'  ReceivedEvent=RawContentBlockStartEvent(content_block=TextBlock(citations=None, text='', type='text'), index=0, type='content_block_start')
[FINE-GRAINED] Claude (streaming text): 
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=TextDelta(text='Here', type='text_delta'), index=0, type='content_block_delta') Here
*** [FINE-GRAINED] ReceivedEventType='text'  ReceivedEvent=TextEvent(type='text', text='Here', snapshot='Here')
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=TextDelta(text=' are your answers:\n\n- 🌤️ **Weather in Tokyo:** It', type='text_delta'), index=0, type='content_block_delta') are your answers:
- 🌤️ **Weather in Tokyo:** It
*** [FINE-GRAINED] ReceivedEventType='text'  ReceivedEvent=TextEvent(type='text', text=' are your answers:\n\n- 🌤️ **Weather in Tokyo:** It', snapshot='Here are your answers:\n\n- 🌤️ **Weather in Tokyo:** It')
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=TextDelta(text="'s currently **22°C** and **partly cloudy**.\n- 🧮 **128 × 4 = 512**", type='text_delta'), index=0, type='content_block_delta') 's currently **22°C** and **partly cloudy**.
- 🧮 **128 × 4 = 512**
*** [FINE-GRAINED] ReceivedEventType='text'  ReceivedEvent=TextEvent(type='text', text="'s currently **22°C** and **partly cloudy**.\n- 🧮 **128 × 4 = 512**", snapshot="Here are your answers:\n\n- 🌤️ **Weather in Tokyo:** It's currently **22°C** and **partly cloudy**.\n- 🧮 **128 × 4 = 512**")
*** [FINE-GRAINED] ReceivedEventType='content_block_delta'  ReceivedEvent=RawContentBlockDeltaEvent(delta=TextDelta(text='\n\nLet me know if you need anything else!', type='text_delta'), index=0, type='content_block_delta') Let me know if you need anything else!
*** [FINE-GRAINED] ReceivedEventType='text'  ReceivedEvent=TextEvent(type='text', text='\n\nLet me know if you need anything else!', snapshot="Here are your answers:\n\n- 🌤️ **Weather in Tokyo:** It's currently **22°C** and **partly cloudy**.\n- 🧮 **128 × 4 = 512**\n\nLet me know if you need anything else!")
*** [FINE-GRAINED] ReceivedEventType='content_block_stop'  ReceivedEvent=ParsedContentBlockStopEvent(index=0, type='content_block_stop', content_block=ParsedTextBlock(citations=None, text="Here are your answers:\n\n- 🌤️ **Weather in Tokyo:** It's currently **22°C** and **partly cloudy**.\n- 🧮 **128 × 4 = 512**\n\nLet me know if you need anything else!", type='text', parsed_output=None))


# eventType MessageDelta
*** [FINE-GRAINED] ReceivedEventType='message_delta'  ReceivedEvent=RawMessageDeltaEvent(delta=Delta(container=None, stop_details=None, stop_reason='end_turn', stop_sequence=None), type='message_delta', usage=MessageDeltaUsage(cache_creation_input_tokens=0, cache_read_input_tokens=0, input_tokens=875, output_tokens=63, server_tool_use=None))
[FINE-GRAINED] stop_reason='end_turn'


# eventType MessageStop
*** [FINE-GRAINED] ReceivedEventType='message_stop'  ReceivedEvent=ParsedMessageStopEvent(type='message_stop', message=ParsedMessage(id='msg_011kUf9zcJSWfN3brsvN8h9i', container=None, content=[ParsedTextBlock(citations=None, text="Here are your answers:\n\n- 🌤️ **Weather in Tokyo:** It's currently **22°C** and **partly cloudy**.\n- 🧮 **128 × 4 = 512**\n\nLet me know if you need anything else!", type='text', parsed_output=None)], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=875, output_tokens=63, server_tool_use=None, service_tier='standard')))


#Log without additional log output
============================================================
APPROACH 2 — FINE-GRAINED (raw SSE events)
============================================================
[FINE-GRAINED] User: What's the weather in Tokyo and what is 128 * 4?
[FINE-GRAINED] Claude (streaming text): I'll look up both at the same time!

[FINE-GRAINED] Tool call starting: get_weather (id=toolu_013LEQgTph3tegRoWPh2z2H4)
[FINE-GRAINED] Streaming tool input JSON: {"city": "Tokyo"}

[FINE-GRAINED] Tool call starting: calculator (id=toolu_013SMDVm4gspc7jBdqcTGx2E)
[FINE-GRAINED] Streaming tool input JSON: {"expression": "128 * 4"}
[FINE-GRAINED] stop_reason='tool_use'
[FINE-GRAINED] Executed get_weather({'city': 'Tokyo'}) → {"city": "Tokyo", "temperature": "22\u00b0C", "condition": "Partly cloudy"}
[FINE-GRAINED] Executed calculator({'expression': '128 * 4'}) → {"result": 512}
[FINE-GRAINED] Sending tool results back, continuing stream...

[FINE-GRAINED] Claude (streaming text): Here are your answers:

- 🌤️ **Weather in Tokyo:** It's currently **22°C** and **partly cloudy**.
- 🔢 **128 × 4 = 512**

Let me know if you need anything else!
[FINE-GRAINED] stop_reason='end_turn'
