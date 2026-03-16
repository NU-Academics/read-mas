# READ-MAS

**Requirements and Design Multi-Agent System**

READ-MAS generates software requirements specifications (SRS) and system designs from natural language queries using multi-agent AI orchestration built on Google ADK. It supports single-agent and multi-agent pipelines, RAG-augmented generation, structured output via Pydantic, and DVC-tracked experiment workflows for training, evaluation, and benchmarking.

## Installation

```bash
git clone <repository-url>
cd read-mas
uv pip install -e .
```

Set environment variables for your LLM provider as needed (e.g. `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`).

## Usage

### Running the CLI

```bash
# Single agent mode
readmas run --query "Design a task management app" -t single_agent -m gemini-2.5-flash

# Multi-agent mode
readmas run --query "Design a chat app" -t read_agent -m gemini-2.5-flash --rag true
```

**Flags:**

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--query` | `-q` | Natural language query describing the software | — |
| `--agent-type` | `-t` | `single_agent` or `read_agent` (multi-agent) | `single_agent` |
| `--llm-model-name` | `-m` | LLM model name | `gemini-2.5-flash` |
| `--rag` | `-r` | Enable RAG retrieval | `false` |
| `--run-id` | `-i` | Unique run identifier | auto-generated |

Outputs are saved to `runs/{run_id}/logs/`.

### RAG Setup

When using `--rag true`, the RAG MCP server must be running first:

```bash
python -m src.rag.retriever_mcp_server
```

This starts the retrieval server on `http://127.0.0.1:8001/mcp`, which provides requirement examples via FAISS + Gemini embeddings.

## Architecture

### Single Agent (`single_agent`)

One `SingleAgent` handles both requirements and design in a single pass.

### Multi-Agent (`read_agent`)

A `SequentialAgent` pipeline with specialized agents for each phase:

```
ReadWrapperAgent
├── RequirementsWrapperAgent
│   └── CollectorAgent → AnalyzerAgent → SpecifierAgent
└── DesignWrapperAgent
    └── DesignerAgent → DocumenterAgent
```

### Key Patterns

- **AgentBase** (`src/agents/agent_base.py`): All agents extend this base class, which provides LLM model init, system prompt, run mode, and RAG config. Each subclass implements `get_agent()` returning a Google ADK `Agent`.
- **LLM routing** (`src/agents/agent_util.py`): Gemini models use native ADK support; Ollama and others are wrapped via LiteLLM.
- **RAG** (`src/rag/retriever.py`): FAISS index over requirement chunks, embedded with Ollama `nomic-embed-text:latest`, returns top-3 results. Registered as a tool on agents when `--rag` is enabled.
- **Structured output**: Collector, Analyzer, and Designer agents produce Pydantic models; downstream agents consume these.

## DVC Experiments

All training, evaluation, and benchmarking stages are defined in `dvc.yaml` and parameterized via `params.yaml`. Run them as DVC experiments:

### Data Setup

Data files (golden test cases, knowledge bases, etc.) are tracked with DVC and must be pulled before running any experiments:

```bash
dvc pull
```

### Training (prompt optimization)

```bash
dvc exp run -S train.agent_name=single_agent -S train.model=gemini-2.5-flash -S train.rag=true --name my-train-exp train
```

### Evaluation

```bash
dvc exp run -S eval.agent_name=single_agent -S eval.model=gemini-2.5-flash -S eval.rag=true --name my-eval-exp eval
```

### Benchmark

```bash
dvc exp run -S benchmark.agent_name=single_agent -S benchmark.model=gemini-2.5-flash -S benchmark.rag=false --name my-bench-exp benchmark
```

### Code Benchmark

Code benchmarking is a multi-step process:

```bash
# Step 1: Generate code samples
python -m src.eval.run generate-samples humaneval -m gemini-2.5-flash --num-samples 2

# Step 2: Sanitize samples with evalplus
evalplus.sanitize --samples data/samples/humaneval/<generated_samples>.jsonl

# Step 3: Run code benchmark with the sanitized file
dvc exp run \
  -S code.agent_name=single_agent \
  -S code.model=gemini-2.5-flash \
  -S code.dataset=humaneval \
  -S code.samples=data/samples/humaneval/<generated_samples>-sanitized.jsonl \
  --name my-code-exp code_benchmark
```

### Viewing Results

```bash
# Compare experiment results
dvc exp show

# Visualize metrics
dvc plots show
```

### params.yaml Structure

```yaml
train:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: true
eval:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: true
benchmark:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: false
code:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: false
  dataset: humaneval
  samples: data/samples/humaneval/<samples_file>-sanitized.jsonl
```

## Eval CLI

The eval CLI (`readmas-eval` or `python -m src.eval.run`) provides direct access to each stage:

```bash
# Training
readmas-eval train -t single_agent -m gemini-2.5-flash -r true -e

# Evaluation
readmas-eval eval -t single_agent -m gemini-2.5-flash -r true -e

# Benchmark
readmas-eval benchmark -t single_agent -m gemini-2.5-flash -r false -e

# Code benchmark
readmas-eval code-benchmark -t single_agent -m gemini-2.5-flash -d humaneval -s <samples_file> -e

# Generate samples
readmas-eval generate-samples humaneval -m gemini-2.5-flash --num-samples 2
```

**Common flags:** `-t` agent type, `-m` model, `-r` RAG toggle, `-e` DVC experiment mode, `-i` run ID.

## Project Structure

```
read-mas/
├── src/
│   ├── agents/           # Base agent classes and utilities
│   ├── requirement/      # Requirements agents (Collector, Analyzer, Specifier)
│   ├── design/           # Design agents (Designer, Documenter)
│   ├── single/           # Single agent implementation
│   ├── orchestrator/     # Agent orchestration and session management
│   ├── rag/              # RAG retriever (FAISS + Ollama embeddings)
│   ├── eval/             # Evaluation framework
│   │   ├── eval_agents/  # Evaluation-specific agents
│   │   ├── evaluators/   # Trainer, evaluator, and benchmarkers
│   │   └── run.py        # Eval CLI entry point
│   ├── prompt_templates/ # System prompts for each agent
│   ├── tools/            # Agent tools (save_to_file, RAG)
│   ├── utils/            # Logging, constants, helpers
│   └── main.py           # Main CLI entry point
├── data/                 # Goldens, samples, and results
├── runs/                 # Execution logs and outputs
├── templates/            # SRS and design document templates
├── kb/                   # Knowledge bases for domain guidance
├── dvc.yaml              # DVC pipeline stages
├── params.yaml           # Experiment parameters
└── pyproject.toml        # Project configuration
```

## Development

```bash
# Run tests
pytest

# Format code (pyink, 2-space indent, 100 char line length)
pyink src/
```

Python >= 3.12 required.

## License

See `LICENSE` file for details.

## Contributing

This is a research project. For contributions or questions, please open an issue.
