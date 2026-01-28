# Copilot Log Converter

Converts GitHub Copilot chat exports (JSON) to readable Markdown files.

## Features

- **Inline References**: Preserves code symbol references with file links (e.g., `` `functionName` ([file.cpp:42](path#L42)) ``)
- **Session Detection**: Automatically archives old files when a new chat session is detected
- **Clean Output**: Removes ANSI escape codes from terminal output
- **Truncation**: Long terminal outputs are truncated to keep files manageable
- **Per-Turn Files**: Each conversation turn is saved as a separate `*_Turn_N.md` file

## Usage

### 1. Export Chat from VS Code

1. Open VS Code with GitHub Copilot Chat
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
3. Type `Chat: Export Chat...` and select it
4. Save the file as `chat.json`

### 2. Run the Converter

```bash
# Basic usage (converts chat.json to chat_Turn_*.md)
python3 copilot_log_converter.py chat.json chat.md

# Specify input and output
python3 copilot_log_converter.py /path/to/export.json /path/to/output.md
```

### Output

```
logs/
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

## Requirements

- Python 3.6+
- No external dependencies

## License

MIT
