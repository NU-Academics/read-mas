"""Prompt templates for the project."""

from .single_prompt import SINGLE_AGENT_SYSTEM_PROMPT
from .collector_prompt import COLLECTOR_AGENT_SYSTEM_PROMPT
from .analyzer_prompt import ANALYZER_AGENT_SYSTEM_PROMPT
from .specifier_prompt import SPECIFIER_AGENT_SYSTEM_PROMPT

__all__ = [
  "COLLECTOR_AGENT_SYSTEM_PROMPT",
  "SINGLE_AGENT_SYSTEM_PROMPT",
  "ANALYZER_AGENT_SYSTEM_PROMPT",
  "SPECIFIER_AGENT_SYSTEM_PROMPT",
  ]
