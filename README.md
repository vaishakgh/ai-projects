# ai-projects

A collection of AI SDK demos and learning projects, organized by platform.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Claude Projects](#claude-projects)
  - [Getting Started](#getting-started)
  - [01 · Anthropic API Fundamentals](#01--anthropic-api-fundamentals)
  - [02 · Prompt Engineering](#02--prompt-engineering)
  - [03 · Tools](#03--tools)
  - [04 · RAG](#04--rag)
  - [05 · Claude Features](#05--claude-features)
- [Azure Projects](#azure-projects)

---

## Project Structure

| Folder | Platform | Status |
|--------|----------|--------|
| [`claude/`](./claude/) | Anthropic Claude API | Active |
| [`azure/`](./azure/) | Azure AI | Coming soon |

---

## Claude Projects

### Getting Started

```bash
cd claude
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your API key to a `.env` file inside `claude/`:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

---

### 01 · Anthropic API Fundamentals

> Core patterns for interacting with the Claude API — authentication, conversation turns, parameters, and streaming.

| File | Description |
|------|-------------|
| [`01_setup.py`](./claude/01_anthropic_api_fundamentals/01_setup.py) | Initial setup and API authentication |
| [`02_single_turn_conversation.py`](./claude/01_anthropic_api_fundamentals/02_single_turn_conversation.py) | Single-turn prompt-response interactions |
| [`03_multi_turn_conversation.py`](./claude/01_anthropic_api_fundamentals/03_multi_turn_conversation.py) | Multi-turn conversations with history management |
| [`04_temperature_system_prompt.py`](./claude/01_anthropic_api_fundamentals/04_temperature_system_prompt.py) | Temperature parameter and system prompt exploration |
| [`05_streaming_conversation.py`](./claude/01_anthropic_api_fundamentals/05_streaming_conversation.py) | Real-time streaming responses |

---

### 02 · Prompt Engineering

> Techniques and strategies for crafting effective prompts, including evaluation and domain-specific examples.

| File | Description |
|------|-------------|
| [`01_prompt_eval.py`](./claude/02_prompt_engg/01_prompt_eval.py) | Evaluating and comparing different prompt strategies |
| [`02_prompt_engineering_nutrition.py`](./claude/02_prompt_engg/02_prompt_engineering_nutrition.py) | Domain-specific prompt engineering using a nutrition use case |

---

### 03 · Tools

> Integrating external tools with Claude — single-turn, multi-turn, and streaming, including a text editor and web search tool.

| File | Description |
|------|-------------|
| [`01_single_turn_with_tools.py`](./claude/03_tools/01_single_turn_with_tools.py) | Tool use in single-turn interactions |
| [`01_single_turn_with_tools_README.md`](./claude/03_tools/01_single_turn_with_tools_README.md) | Documentation for single-turn tool usage |
| [`02_multi_turn_with_tools.py`](./claude/03_tools/02_multi_turn_with_tools.py) | Tool use across multi-turn conversations |
| [`03_streaming_with_tools.py`](./claude/03_tools/03_streaming_with_tools.py) | Streaming responses combined with tool integration |
| [`03_streaming_with_tools_README.md`](./claude/03_tools/03_streaming_with_tools_README.md) | Documentation for streaming with tools |
| [`04_text_editor_tool.py`](./claude/03_tools/04_text_editor_tool.py) | Text editing as a Claude tool |
| [`05_web_search_tool.py`](./claude/03_tools/05_web_search_tool.py) | Web search as a Claude tool |

---

### 04 · RAG

> Retrieval-Augmented Generation — combining Claude with external knowledge sources.

_Coming soon._

---

### 05 · Claude Features

> Demonstrations of advanced Claude capabilities beyond the core API.

| File | Description |
|------|-------------|
| [`01_extended_thinking.py`](./claude/05_claude_features/01_extended_thinking.py) | Extended thinking for complex, multi-step reasoning |

---

## Azure Projects

> Azure AI integration projects are planned for a future release.

_To be published — watch this space._
