# 03 - Tools

Demonstrates how to use Claude's tool-calling feature (function calling) with the Anthropic API.

---

## Files

- `01_single_turn_with_tools.py` — Single user prompt with tool use resolved before returning.


---

## Sample Log Output — `01_single_turn_with_tools.py`

### Prompt: "What's the weather like in Tokyo right now?"

#### Simplified Log
```
Claude Initial response: Message(
  content=[ToolUseBlock(input={'city': 'Tokyo'}, name='get_weather', type='tool_use')],
  stop_reason='tool_use')

  [tool call] get_weather({'city': 'Tokyo'})
  [tool result] {"city": "Tokyo", "temperature": "22°C", "condition": "Partly cloudy"}

Claude Final response: Message(
  content=[TextBlock(text='The current weather in **Tokyo** is **22°C** and **partly cloudy**.')],
  stop_reason='end_turn')

Claude: The current weather in **Tokyo** is **22°C** and **partly cloudy**. It sounds like a mild and pleasant day! 🌤️

```

---

### Prompt: "What is 347 * 19?"

#### Simplified Log
```
Claude Initial response: Message(
  content=[ToolUseBlock(input={'expression': '347 * 19'}, name='calculator', type='tool_use')],
  stop_reason='tool_use')

  [tool call] calculator({'expression': '347 * 19'})
  [tool result] {"result": 6593}

Claude Final response: Message(
  content=[TextBlock(text='The result of **347 × 19 = 6,593**.')],
  stop_reason='end_turn')

Claude: The result of **347 × 19 = 6,593**.
```

---

### Prompt: "What is the weather now in China?"

Claude asks for clarification (no tool call made — city not specific enough):

#### Simplified Log
```
Claude: China is a vast country with many cities, each potentially having different weather
conditions. Could you please specify which city in China you'd like to know the weather for?
```

---

### Prompt: "What is the weather now in New York? Add 345 and 567 together for me as well, please."

Claude calls **both tools in parallel** in a single response:

#### Simplified Log
```
Claude Initial response: Message(
  content=[
    TextBlock(text='Sure! Let me fetch the weather in New York and calculate that sum at the same time!'),
    ToolUseBlock(input={'city': 'New York'}, name='get_weather'),
    ToolUseBlock(input={'expression': '345 + 567'}, name='calculator')
  ],
  stop_reason='tool_use')

  [tool call] get_weather({'city': 'New York'})
  [tool result] {"city": "New York", "temperature": "22°C", "condition": "Partly cloudy"}
  [tool call] calculator({'expression': '345 + 567'})
  [tool result] {"result": 912}

Claude: 🌤️ Weather in New York: 22°C, Partly Cloudy
        🧮 345 + 567 = 912
```

---

## Key Lines in `01_single_turn_with_tools.py`

| Line | What it does |
|------|-------------|
| 76   | Initial user message added to `messages` list |
| 94   | Claude's response (with tool_use blocks) appended as `assistant` turn |
| 109  | Tool results sent back as a `user` turn |

> See the [Anthropic tool use flow diagram](https://anthropic.skilljar.com/claude-with-the-anthropic-api/287752) to understand the message structure across lines 94 and 109.

---

## Full Log Output

```


User  : What's the weather like in Tokyo right now?
Claude Initial response: Message(
id='msg_01XhbodiThh3tS2GEaP4aHeL', container=None, 
content=[ToolUseBlock(id='toolu_01Gx5KpBJLs2i5ZZiPkHbSvj', caller=DirectCaller(type='direct'), input={'city': 'Tokyo'}, name='get_weather', type='tool_use')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=669, output_tokens=54, server_tool_use=None, service_tier='standard'))
  [tool call] get_weather({'city': 'Tokyo'})
  [tool result] {"city": "Tokyo", "temperature": "22\u00b0C", "condition": "Partly cloudy"}
Claude Final response: Message(id='msg_01BGmCnsxRUJuYTQu4ZyBRom', container=None, content=[TextBlock(citations=None, text='The current weather in Tokyo is **22°C** and **partly cloudy**. It sounds like a mild and pleasant day! Would you like to know anything else?', type='text')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=762, output_tokens=38, server_tool_use=None, service_tier='standard'))
Claude: The current weather in Tokyo is **22°C** and **partly cloudy**. It sounds like a mild and pleasant day! Would you like to know anything else?


User  : What is 347 * 19?
Claude Initial response: Message(id='msg_017VWTzjMyg3ZyswPeVkJnyM', container=None, content=[ToolUseBlock(id='toolu_01FHbfFymyNSinNPPGGwmJDt', caller=DirectCaller(type='direct'), input={'expression': '347 * 19'}, name='calculator', type='tool_use')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=668, output_tokens=56, server_tool_use=None, service_tier='standard'))
  [tool call] calculator({'expression': '347 * 19'})
  [tool result] {"result": 6593}
Claude Final response: Message(id='msg_01XvcgPYmuz8vR6cQAjQsHmD', container=None, content=[TextBlock(citations=None, text='The result of **347 × 19 = 6,593**.', type='text')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=742, output_tokens=19, server_tool_use=None, service_tier='standard'))
Claude: The result of **347 × 19 = 6,593**.


User  : What is the weather now in China?
Claude Initial response: Message(id='msg_01CUbJJ3rwwAJsvprPMMSpc5', container=None, content=[TextBlock(citations=None, text="China is a vast country with many cities, each potentially having different weather conditions. Could you please specify which **city in China** you'd like to know the weather for? For example:\n\n- **Beijing**\n- **Shanghai**\n- **Guangzhou**\n- **Shenzhen**\n- **Chengdu**", type='text')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=667, output_tokens=74, server_tool_use=None, service_tier='standard'))
Claude: China is a vast country with many cities, each potentially having different weather conditions. Could you please specify which **city in China** you'd like to know the weather for? For example:

- **Beijing**
- **Shanghai**
- **Guangzhou**
- **Shenzhen**
- **Chengdu**


User  : What is the weather now in New York? Add 345 and 567 together for me as well, please.
Claude Initial response: Message(id='msg_01Lp3EZNcJJRMog4H5UL7ELj', container=None, 
content=[TextBlock(citations=None, text="Sure! I'll fetch the current weather in New York and calculate the sum of 345 and 567 at the same time!", type='text'), 
ToolUseBlock(id='toolu_01JkE5udAM7WZ8ZFDPJnUUhv', caller=DirectCaller(type='direct'), input={'city': 'New York'}, name='get_weather', type='tool_use'), 
ToolUseBlock(id='toolu_01CfckgETfgTFnpgVjsXGpj2', caller=DirectCaller(type='direct'), input={'expression': '345 + 567'}, name='calculator', type='tool_use')], 
model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='tool_use', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=684, output_tokens=121, server_tool_use=None, service_tier='standard'))

  [tool call] get_weather({'city': 'New York'})
  [tool result] {"city": "New York", "temperature": "22\u00b0C", "condition": "Partly cloudy"}
  [tool call] calculator({'expression': '345 + 567'})
  [tool result] {"result": 912}

Claude Final response: Message(id='msg_01KxDicCvLaHx19KjsMU4ENN', container=None, content=[TextBlock(citations=None, text="Here are your results:\n\n1. 🌤️ **Weather in New York:** It's currently **22°C** with **partly cloudy** skies.\n2. ➕ **345 + 567 = 912**\n\nLet me know if there's anything else I can help you with!", type='text')], model='claude-sonnet-4-6', role='assistant', stop_details=None, stop_reason='end_turn', stop_sequence=None, type='message', usage=Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, inference_geo='global', input_tokens=899, output_tokens=73, server_tool_use=None, service_tier='standard'))
Claude: Here are your results:

1. 🌤️ **Weather in New York:** It's currently **22°C** with **partly cloudy** skies.
2. ➕ **345 + 567 = 912**

Let me know if there's anything else I can help you with!
```