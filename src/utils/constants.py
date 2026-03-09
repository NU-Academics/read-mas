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
  MAIN = "main"


NUMBER_OF_TRIES = 2

EVALUATION_MODEL = "gpt-5-mini"
