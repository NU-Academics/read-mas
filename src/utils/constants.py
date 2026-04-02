"""Constants common across modules are defined here."""

from enum import StrEnum

DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL_NAME = f"{DEFAULT_PROVIDER}_chat/gpt-oss:20b"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_API_BASE = f"{OLLAMA_BASE_URL}/v1"


class AgentRunMode(StrEnum):
  """Run modes for the READ-MAS agents: eval, benchmark, or main"""

  TRAIN = "train"
  EVAL = "eval"
  BENCHMARK = "benchmark"
  CODE_BENCHMARK = "code_benchmark"
  LLM_BENCHMARK = "llm_benchmark"
  MAIN = "main"


class ExecMode(StrEnum):
  """Execution modes: local runs everything inline; remote uses MCP and A2A servers."""

  LOCAL = "local"
  REMOTE = "remote"


NUMBER_OF_TRIES = 2

EVALUATION_MODEL = "gpt-4.1"

MCP_URL_RAG = "http://127.0.0.1:8001/mcp"

THINKING_BUDGET = 8192

DESIGN_A2A_PORT = 8003

RE_A2A_PORT = 8002
