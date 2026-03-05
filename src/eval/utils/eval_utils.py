"""Utility functions for the evaluation module."""

import json
from typing import Optional

from deepeval.dataset import Golden
from deepeval.metrics import BaseMetric
from deepeval.prompt import Prompt
from google.adk.agents import BaseAgent

from eval.utils.constants import (
  AGENT_GOLDENS_MAP,
  AGENT_METRICS_MAP,
  AGENT_RAG_METRICS_MAP,
  AGENT_PROMPTS,
  AGENT_REGISTRY,
)
from rag import retrieve_requirements
from utils.constants import AgentRunMode


def get_metrics(agent_type: str, rag: bool = False) -> list[BaseMetric]:
  """Gets the list of metrics for an agent."""
  if rag:
    return AGENT_RAG_METRICS_MAP[agent_type]
    
  return AGENT_METRICS_MAP[agent_type]


def get_prompt(agent_type: str) -> Prompt:
  """Gets an agent's system prompt as a Prompt object."""
  return AGENT_PROMPTS[agent_type]


def get_eval_agent(agent_type: str, model: str, prompt: Optional[str], rag: bool, run_mode: Optional[AgentRunMode] = AgentRunMode.EVAL) -> BaseAgent:
  """Gets the agent to be evaluated."""
  agent = AGENT_REGISTRY[agent_type]
  return agent(model, prompt, run_mode, rag).get_agent()


def get_goldens(agent_type: str, rag: bool, run_mode: Optional[AgentRunMode] = AgentRunMode.EVAL) -> list[Golden]:
  """Retrieves a list of goldens for an agent based on the requested run mode."""
  golden_filename = run_mode.value + ".json"
  golden_path = AGENT_GOLDENS_MAP[agent_type] / golden_filename
  with open(golden_path, "r") as jf:
    goldens_list = json.load(jf)

  goldens = [Golden.model_validate(g) for g in goldens_list]
  
  if rag:
    for golden in goldens:
      retrieval_context = retrieve_requirements(golden.input)
      golden.retrieval_context = retrieval_context or None
      
  return goldens

