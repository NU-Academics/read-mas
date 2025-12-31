"""Constants common across modules are defined here."""

from enum import StrEnum

DEFAULT_MODEL_NAME = "ollama_chat/gpt-oss:20b"


class AgentRunMode(StrEnum):
  """Run modes for the READ-MAS agents: eval, benchmark, or main"""

  EVAL = "EVAL"
  BENCHMARK = "BENCHMARK"
  MAIN = "MAIN"


NUMBER_OF_TRIES = 2
