"""Utility functions for the evaluation module."""

import json
from typing import Optional
from loguru import logger

from deepeval.dataset import Golden
from deepeval.evaluate.types import EvaluationResult
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


def get_eval_agent(
    agent_type: str,
    model: str,
    prompt: Optional[str],
    rag: bool,
    run_mode: Optional[AgentRunMode] = AgentRunMode.EVAL,
) -> BaseAgent:
  """Gets the agent to be evaluated."""
  agent = AGENT_REGISTRY[agent_type]
  return agent(model, prompt, run_mode, rag).get_agent()


def get_goldens(
    agent_type: str, rag: bool, run_mode: Optional[AgentRunMode] = AgentRunMode.EVAL
) -> list[Golden]:
  """Retrieves a list of goldens for an agent based on the requested run mode."""
  golden_filename = run_mode.value + '.json'
  golden_path = AGENT_GOLDENS_MAP[agent_type] / golden_filename
  with open(golden_path, 'r') as jf:
    goldens_list = json.load(jf)

  goldens = [Golden.model_validate(g) for g in goldens_list]

  if rag:
    for golden in goldens:
      retrieval_context = retrieve_requirements(golden.input)
      golden.retrieval_context = retrieval_context or None

  return goldens


def get_eval_result(
    eval_results: EvaluationResult, agent_name: str, model: str, rag: bool
) -> list[dict[str, bool | str | float]]:
  result = [
      {
          'agent': agent_name,
          'model': model,
          'rag': rag,
          'test_name': test.name,
          'metric': m.name,
          'score': m.score,
          'cost': m.evaluation_cost,
          'threshold': m.threshold,
          'success': m.success,
          'reason': m.reason,
      }
      for test in eval_results.test_results
      for m in test.metrics_data
  ]
  logger.debug(f"Eval results: {str(result)}")
  return result

def compute_metrics_averages(metric_list):
    """
    Compute the average score for each metric in the list.
    """
    totals   = {}
    counters = {}

    for entry in metric_list:
        m = entry['metric']
        s = entry['score']
        totals[m]   = totals.get(m, 0.0) + s
        counters[m] = counters.get(m, 0)   + 1

    averages = [{'metric': m, 'score': float(f"{totals[m] / counters[m]:.3f}")} for m in totals]
    return averages

if __name__ == "__main__":
  metrics = [{'metric': 'accuracy', 'score': 0.8},{'metric': 'accuracy', 'score': 0.7},{'metric': 'faithfulness', 'score': 0.9},{'metric': 'faithfulness', 'score': 0.8}]
  averages = compute_metrics_averages(metrics)
  print(f"Metric averages: {str(averages)}")