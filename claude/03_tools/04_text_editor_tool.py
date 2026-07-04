"""
04 - Text Editor Tool
Demonstrates Claude's built-in text editor tool.

Unlike custom tools (get_weather, calculator), the text editor tool is
declared with a built-in type string — Claude already knows its full
interface from training. No input_schema is required.

Commands Claude can invoke:
  view        — read a file (with optional line range) or list a directory
  create      — create a new file with given content
  str_replace — replace an exact string in a file (first match only)
  insert      — insert lines after a specific line number
  undo_edit   — revert the last edit on a file
"""

import os
import tempfile
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Tool type is model-specific. Check supported types from the API error message if unsure.
# claude-sonnet-4-6 → text_editor_20250728
# claude-sonnet-4-5 → text_editor_20250429
# claude-3-7        → text_editor_20250124
# claude-3-5        → text_editor_20241022
MODEL = "claude-sonnet-4-6"

TEXT_EDITOR_TOOL = {
    "type": "text_editor_20250728",
    "name": "str_replace_based_edit_tool",
}


# --- Text editor command handlers -----------------------------------------------

def run_text_editor(command: str, inputs: dict) -> str:
    """Execute a text editor command locally and return a result string."""
    path = inputs.get("path", "")

    if command == "view":
        if os.path.isdir(path):
            try:
                return "\n".join(sorted(os.listdir(path)))
            except Exception as e:
                return f"Error listing directory: {e}"
        try:
            with open(path, "r") as f:
                lines = f.readlines()
            view_range = inputs.get("view_range")
            if view_range:
                start, end = view_range[0] - 1, view_range[1]
                lines = lines[start:end]
            return "".join(f"{i + 1}\t{l}" for i, l in enumerate(lines))
        except FileNotFoundError:
            return f"Error: file not found: {path}"
        except Exception as e:
            return f"Error: {e}"

    if command == "create":
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w") as f:
                f.write(inputs.get("file_text", ""))
            return f"Created: {path}"
        except Exception as e:
            return f"Error creating file: {e}"

    if command == "str_replace":
        try:
            with open(path, "r") as f:
                content = f.read()
            old_str = inputs.get("old_str", "")
            new_str = inputs.get("new_str", "")
            if old_str not in content:
                return f"Error: old_str not found in {path}"
            with open(path, "w") as f:
                f.write(content.replace(old_str, new_str, 1))
            return f"Replaced in {path}"
        except Exception as e:
            return f"Error: {e}"

    if command == "insert":
        try:
            with open(path, "r") as f:
                lines = f.readlines()
            insert_after = inputs.get("insert_line", 0)
            new_lines = inputs.get("new_str", "").splitlines(keepends=True)
            lines[insert_after:insert_after] = new_lines
            with open(path, "w") as f:
                f.writelines(lines)
            return f"Inserted {len(new_lines)} line(s) after line {insert_after} in {path}"
        except Exception as e:
            return f"Error: {e}"

    if command == "undo_edit":
        return "undo_edit is not supported in this demo — no edit history is tracked."

    return f"Error: unknown command '{command}'"


# --- Agentic loop ---------------------------------------------------------------

def run_agent(client: anthropic.Anthropic, task: str) -> None:
    """
    Send a task to Claude and loop until it finishes, executing any
    text editor tool calls along the way.
    """
    print(f"Task: {task}")
    messages = [{"role": "user", "content": task}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=[TEXT_EDITOR_TOOL],
            messages=messages,
        )

        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"Claude: {block.text}")

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                command = block.input.get("command", "")
                print(f"  [tool call] {command}  input={block.input}")
                result = run_text_editor(command, block.input)
                print(f"  [tool result] {result[:200]}{'...' if len(result) > 200 else ''}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

    print()


# --- Entry point ----------------------------------------------------------------

if __name__ == "__main__":
    client = anthropic.Anthropic()

    # Create a temporary Python file for Claude to work with.
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    tmp.write(
        "def greet(name):\n"
        "    print('Hello')\n"
        "\n"
        "greet('World')\n"
    )
    tmp.close()
    path = tmp.name
    print(f"Working file: {path}\n")
    print("=" * 60)

    # Task 1: view the file
    run_agent(client, f"View the file at {path} and describe what it does.")
    print("=" * 60)

    # Task 2: fix a bug — greet() ignores its name parameter
    run_agent(
        client,
        f"The greet() function in {path} ignores its name parameter and always "
        f"prints 'Hello'. Fix it so it prints 'Hello, <name>!' using the parameter.",
    )
    print("=" * 60)

    # Task 3: add a new function
    run_agent(
        client,
        f"Add a farewell() function to {path} that takes a name and prints "
        f"'Goodbye, <name>!'. Then add a call to farewell('World') at the bottom.",
    )
    print("=" * 60)

    # Task 4: view final state
    run_agent(client, f"Show me the final contents of {path}.")
    print("=" * 60)

    os.unlink(path)
    print(f"Cleaned up {path}")
