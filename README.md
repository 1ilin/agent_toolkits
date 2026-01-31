# Agent Toolkits

A curated collection of practical tools and skills for working with AI agents. This repository serves as a personal toolkit for enhancing agent-based workflows, improving productivity, and bridging the gap between humans and AI assistants.

## 🎯 Vision

As AI agents become more integrated into our development workflows, we need better tools to:
- **Manage and preserve** agent interactions
- **Analyze and improve** prompt patterns
- **Share and reuse** effective agent skills
- **Debug and verify** agent outputs
- **Automate workflows** involving multiple agents

This repository is a growing collection of utilities designed to make working with AI agents more efficient, transparent, and enjoyable.

## 📦 Current Tools

### [Copilot Log Converter](./github-copilot/)

Converts GitHub Copilot VS Code chat exports (JSON) to readable Markdown files.

**Why it matters:**
- 📖 Transform bulky JSON exports into clean, organized Markdown archives
- 🔄 Enable cross-verification between agent sessions (reduce hallucination)
- 📊 Analyze successful prompt chains for pattern recognition
- 🤝 Share effective human-AI communication examples

**Key Features:**
- 3 output modes: `agent` (flat), `human` (VS Code-style), `fullout` (verbose)
- Automatic session detection and archiving
- Terminal output truncation and ANSI cleaning
- Per-turn file generation with smart merging

[→ Full documentation](./github-copilot/copilot_log_converter.md)

## 🚀 Getting Started

Each tool in this repository is self-contained with its own documentation. Navigate to the tool's directory for specific usage instructions.

### Quick Example: Copilot Log Converter

```bash
# Export your chat from VS Code (Ctrl+Shift+P → "Chat: Export Chat...")
# Then convert it to readable Markdown
cd github-copilot
python3 copilot_log_converter.py chat.json

# Or use different output modes
python3 copilot_log_converter.py -human chat.json output.md
python3 copilot_log_converter.py -fullout chat.json
```

## 🗺️ Roadmap

Future tools and skills planned for this collection:

- **Multi-Agent Orchestration**: Tools for coordinating multiple agents
- **Prompt Template Library**: Reusable, tested prompt patterns
- **Agent Performance Analytics**: Metrics and analysis for agent outputs
- **Context Management**: Tools for managing long-context conversations
- **Cross-Platform Log Converters**: Support for Claude, ChatGPT, and other platforms
- **Agent Memory Systems**: Persistent knowledge bases for agents
- **Verification Tools**: Automated checks for agent hallucinations

## 🛠️ Contributing

This is a personal toolkit, but contributions are welcome! If you have:
- Bug fixes or improvements for existing tools
- New tools that fit the agent workflow theme
- Documentation improvements
- Use cases or examples

Feel free to open an issue or submit a pull request.

### Development Guidelines

- Keep tools **self-contained** with minimal dependencies
- Provide **clear documentation** with examples
- Follow **existing code style** in each tool's language
- Include **usage examples** in tool READMEs

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

## 🤝 Acknowledgments

Built with and for AI agents. Special thanks to the communities building:
- GitHub Copilot
- Claude (Anthropic)
- ChatGPT (OpenAI)
- And all the developers pushing the boundaries of human-AI collaboration

---

**Note**: This is an evolving collection. Tools are added as needs arise from real-world agent workflows. Star the repo to follow updates! ⭐
