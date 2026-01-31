# Copilot Log Converter

Converts GitHub Copilot chat exports (JSON) to readable Markdown files. 

## Why this tool?

1. **Readable Archives**: VS Code currently only exports chat history as JSON files, which are bulky and hard to read directly. This tool converts them into clean, organized Markdown.
2. **Agentic Vibe Coding**: In "vibe coding" workflows, verifying that an agent isn't hallucinating or making mistakes can be exhausting. Converting logs to Markdown makes it easier to feed one agent session's output into another for cross-verification, reducing human workload and overcoming local optima through multi-agent debate.
3. **Show Your Talk**: Code is cheap, show me your talk! Exporting successful prompt chains helps in analyzing and sharing effective communication patterns, improving the collaboration experience between humans and AI agents.

## Features

- **Session Detection**: Automatically archives old files when a new chat session is detected
- **Truncation**: Long terminal outputs are truncated to keep files manageable
- **Per-Turn Files**: Each conversation turn is saved as a separate `*_turn_N.md` file
- **Turn Merging**: Automatically merges turns where the user only says "Continue" into the previous turn's file (e.g., `_turn_6-7.md`)


## Usage

### 1. Export Chat from VS Code

1. Open VS Code with GitHub Copilot Chat
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
3. Type `Chat: Export Chat...` and select it
4. Save the file as `chat.json` in the same directory as the converter script

> **Note**: The export process is currently manual via GUI only. Automation via CLI is not supported by VS Code at this time. PR contributions for workarounds are welcome!

### 2. Run the Converter

```bash
# Basic usage (defaults to -agent mode, will convert chat.json if no args given)
python3 copilot_log_converter.py [input.json] [output.md]

# Select Output Mode:
python3 copilot_log_converter.py -agent    # [Default] Flat format, hidden edits, code block thinking
python3 copilot_log_converter.py -human    # VS Code style, HTML folded thinking/edits, timestamps
python3 copilot_log_converter.py -fullout  # Verbose, shows all edits and full terminal output
```

## Output Modes

The converter supports three distinct modes to suit different workflows:

| Mode | Flag | Description | Thinking Format | Edits | Terminal |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Agent** | `-agent` | **Default**. Optimized for machine reading and context injection. Clean, flat structure. | `Thinking：` + Code Block | Hidden (File path only) | Truncated |
| **Human** | `-human` | Optimized for human review. mimicks VS Code UI. | HTML `<details>` (Folded) | Folded | Truncated + **Timestamps** |
| **Fullout** | `-fullout` | Maximum verbosity for debugging or auditing. | `Thinking：` + Code Block | Full Content | **Full Output** |


### Output

```
your-directory/
├── chat.json           # Exported from VS Code
├── chat.session        # Session ID tracker
├── chat_Turn_1.md      # First conversation turn
├── chat_Turn_2.md      # Second turn
├── ...
└── archive_YYYYMMDD_HHMMSS/  # Archived files from previous sessions
```

## Session Management

The converter tracks sessions using the first request's ID. When you export a **new** chat session:

1. Old `*_Turn_*.md` files are moved to an `archive_YYYYMMDD_HHMMSS/` folder
2. New turn files are generated from the current JSON

This prevents confusion between turns from different sessions.

## Notations

- GitHub Copilot uses a "copy on write" approach when modifying code. The agent first prepares the complete modified code, then applies it as a patch to overwrite the old code. As a result, the exported `chat.json` only contains the final complete code for each turn — the original code and diffs are not preserved.


## License

MIT
