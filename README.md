# READ-MAS

**Requirements and Design Multi-Agent System**

An automated software requirements specification (SRS) and system design generation system powered by multi-agent AI orchestration. READ-MAS uses Large Language Models (LLMs) to generate comprehensive software requirements and architectural designs from natural language queries.

## Features

- 🤖 **Single Agent Mode**: Unified agent that generates both requirements and system design
- 🔄 **Multi-Agent Support**: Architecture ready for multi-agent workflows (coming soon)
- 🎯 **LLM Flexibility**: Support for multiple LLM providers via LiteLLM
- 📝 **Comprehensive Output**: Generates detailed SRS documents with system architecture
- 🔌 **Google ADK Integration**: Built on Google's Agent Development Kit for robust agent orchestration
- 📊 **Session Management**: Tracks conversation state and agent interactions
- 🖥️ **CLI Interface**: Easy-to-use command-line interface powered by Typer

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd read-mas
   ```

2. **Install dependencies**:
   ```bash
   uv pip install -e .
   ```

   Or with pip:
   ```bash
   pip install -e .
   ```

3. **Configure your LLM provider** (if needed):
   - Set environment variables for your LLM provider (OpenAI, Anthropic, Ollama, etc.)
   - Default model: `ollama_chat/gpt-oss:20b` (configured in `src/orchestrator/constants.py`)

## Usage

### Command-Line Interface

After installation, you can use the CLI in two ways:

#### Option 1: Using the installed command
```bash
readmas --query "Design a tic-tac-toe game" -t single -m ollama_chat/gpt-oss:20b
```

#### Option 2: Running as a module
```bash
python -m src.main --query "Design a tic-tac-toe game" -t single -m ollama_chat/gpt-oss:20b
```

### Command Options

- `--query`, `-q`: User's input query describing the software to design (required)
- `--agent-type`, `-t`: Agent type - `single` or `multi` (default: `single`)
- `--llm-model-name`, `-m`: LLM model name to use (default: `ollama_chat/gpt-oss:20b`)
- `--run-id`, `-r`: Unique run identifier (default: auto-generated UUID)

### Example

```bash
python -m src.main \
  --query "Design a task management application with user authentication and team collaboration features" \
  --agent-type single \
  --llm-model-name "gpt-4"
```

## Project Structure

```
read-mas/
├── src/
│   ├── agents/          # Base agent classes and utilities
│   │   ├── agent_base.py
│   │   └── agent_util.py
│   ├── orchestrator/    # Agent orchestration and session management
│   │   ├── orchestrator.py
│   │   ├── session_manager.py
│   │   └── constants.py
│   ├── single/          # Single agent implementation
│   │   └── single_agent.py
│   ├── design/          # Design-related modules (future)
│   ├── requirement/     # Requirements-related modules (future)
│   └── main.py          # CLI entry point
├── notebooks/           # Jupyter notebooks for experimentation
├── runs/                # Execution logs and outputs
├── pyproject.toml       # Project configuration and dependencies
└── README.md
```

## Architecture

READ-MAS is built on Google's Agent Development Kit (ADK) and follows a modular architecture:

- **Orchestrator**: Routes queries to appropriate agent(s) and manages execution flow
- **Session Manager**: Handles session state and agent interactions
- **Single Agent**: Unified agent that handles both requirements elicitation and system design
- **LLM Integration**: Uses LiteLLM for multi-provider LLM support

### Current Agent Types

#### Single Agent (`single`)
A unified agent that:
1. Analyzes the user's query
2. Generates comprehensive Software Requirements Specification (SRS)
3. Creates detailed system design documentation
4. Outputs structured documentation including:
   - Functional and non-functional requirements
   - System architecture
   - Component details
   - Data structures
   - Algorithmic specifications
   - Test plans
   - Deployment considerations

## Configuration

### Default Model

The default LLM model can be changed in `src/orchestrator/constants.py`:

```python
DEFAULT_MODEL_NAME = "ollama_chat/gpt-oss:20b"
```

### Supported LLM Providers

READ-MAS supports any LLM provider compatible with LiteLLM, including:
- OpenAI (GPT-3.5, GPT-4, etc.)
- Anthropic (Claude)
- Ollama (local models)
- Google (Gemini)
- And many more...

### Environment Variables

Set the following environment variables based on your LLM provider:

```bash
# OpenAI
export OPENAI_API_KEY="your-key-here"

# Anthropic
export ANTHROPIC_API_KEY="your-key-here"

# Ollama (usually runs locally, no API key needed)
export OLLAMA_BASE_URL="http://localhost:11434"
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

The project uses Pyink (based on Black) for code formatting:

```bash
pyink src/
```

### Project Dependencies

Key dependencies:
- `google-adk[a2a]`: Google Agent Development Kit
- `litellm`: Multi-provider LLM interface
- `typer`: CLI framework
- `rich`: Enhanced terminal output
- `loguru`: Logging

See `pyproject.toml` for the complete list of dependencies.

## Output

The system generates comprehensive documentation including:

1. **Software Requirements Specification (SRS)**
   - Introduction and scope
   - Functional and non-functional requirements
   - User classes and characteristics
   - Operating environment
   - External interfaces

2. **System Design**
   - Architectural overview
   - Component details
   - Data structures
   - Algorithmic specifications
   - UI/UX flow
   - Deployment considerations

3. **Test Plan**
   - High-level test cases
   - Expected results

All outputs are saved to log files in the `runs/` directory for each execution.

## License

See `LICENSE` file for details.

## Contributing

This is a research project. For contributions or questions, please open an issue or contact the maintainers.

## Acknowledgments

- Built with [Google ADK](https://github.com/google/generative-ai-python)
- LLM integration via [LiteLLM](https://github.com/BerriAI/litellm)
