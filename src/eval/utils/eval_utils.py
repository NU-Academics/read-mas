"""Utility functions for the evaluation module."""

import json
import math
from typing import Any, Optional

import pandas as pd
from loguru import logger

from deepeval.dataset import EvaluationDataset
from deepeval.dataset import Golden
from deepeval.evaluate.types import EvaluationResult
from deepeval.metrics import BaseMetric
from deepeval.prompt import Prompt
from dvclive.live import Live
from google.adk.agents import BaseAgent
from langchain_openai import ChatOpenAI
from ragas import evaluate as ragas_evaluate
from ragas import EvaluationDataset as RagasEvaluationDataset, SingleTurnSample

from eval.metrics import (
  RAGAS_COMBINED,
  RAGAS_FAITHFULNESS,
  RAGAS_ALL_METRICS,
  RAGAS_FAITHFULNESS_ONLY,
)
from eval.utils.constants import (
    AGENT_GOLDENS_MAP,
    AGENT_METRICS_MAP,
    AGENT_RAG_METRICS_MAP,
    AGENT_RAGAS_METRICS_MAP,
    AGENT_PROMPTS,
    AGENT_REGISTRY,
)
from rag import retrieve_requirements
from utils.constants import (
  AgentRunMode,
  EVALUATION_MODEL,
)


def get_metrics(agent_type: str, rag: bool = False) -> list[BaseMetric]:
  """Gets the list of DeepEval metrics for an agent."""

  if rag:
    return AGENT_RAG_METRICS_MAP[agent_type]

  return AGENT_METRICS_MAP[agent_type]


def get_ragas_metric_names(agent_type: str, rag: bool = False) -> list[str]:
  """Gets the list of RAGAS metric names to run for an agent (only when RAG is enabled)."""
  if not rag:
    return []
  return AGENT_RAGAS_METRICS_MAP.get(agent_type, [])


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


def get_dataset(
    agent_type: str, rag: bool, run_mode: Optional[AgentRunMode] = AgentRunMode.EVAL
) -> EvaluationDataset:
  """Retrieves an evaluation dataset with a list of goldens for an agent based on the requested run mode."""
  golden_filename = run_mode.value + '.json'
  golden_path = AGENT_GOLDENS_MAP[agent_type] / golden_filename
  with open(golden_path, 'r') as jf:
    goldens_list = json.load(jf)

  goldens = [Golden.model_validate(g) for g in goldens_list]

  if rag:
    for golden in goldens:
      retrieval_context = retrieve_requirements(golden.input)
      golden.retrieval_context = retrieval_context or None

  dataset = EvaluationDataset(goldens=goldens)
  return dataset


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
          'success': m.success if m.success is not None else False,
          'reason': m.reason,
      }
      for test in eval_results.test_results
      for m in test.metrics_data
  ]
  return result

def _sanitize_score(score):
  """Convert NaN scores to 0 and numpy types to Python floats. Ragas returns
  NaN when it cannot extract statements from the answer (0/0), which poisons
  downstream aggregation. Pandas also returns numpy.float64 which should be
  cast to plain float for clean serialization."""
  if score is None:
    logger.debug("RAGAS score is None, defaulting to 0.0")
    return 0.0
  score = float(score)
  if math.isnan(score):
    logger.debug("RAGAS score is NaN, defaulting to 0.0")
    return 0.0
  return score

def _evaluate_samples_individually(samples, metrics, llm):
  """Evaluate RAGAS samples one at a time, isolating failures."""
  rows = []
  for i, sample in enumerate(samples):
    try:
      dataset = RagasEvaluationDataset(samples=[sample])
      result = ragas_evaluate(dataset, metrics=metrics, llm=llm)
      row = result.to_pandas().iloc[0].to_dict()
    except Exception as e:
      logger.warning(f"RAGAS evaluation failed for sample {i} ({type(e).__name__}: {e})")
      row = {m.name: float('nan') for m in metrics}
    rows.append(row)
  return pd.DataFrame(rows)


def _run_ragas_evaluation(
    test_cases: list[dict],
    ragas_metric_names: list[str],
    threshold: float = 0.5,
) -> list[dict]:
  """Run RAGAS metrics directly via the ragas library.

  Args:
    test_cases: List of dicts with keys: input, actual_output, expected_output,
                retrieval_context (list[str]).
    ragas_metric_names: Which RAGAS metric sets to run (RAGAS_FAITHFULNESS, RAGAS_COMBINED).
    threshold: Score threshold for success.

  Returns:
    List of result dicts matching the format from get_eval_result:
    [{metric, score, threshold, success, reason}, ...]
  """
  if not ragas_metric_names:
    return []

  llm = ChatOpenAI(model=EVALUATION_MODEL)

  # Determine which ragas metrics to run.
  metrics_to_run = []
  if RAGAS_COMBINED in ragas_metric_names:
    metrics_to_run = RAGAS_ALL_METRICS
  elif RAGAS_FAITHFULNESS in ragas_metric_names:
    metrics_to_run = RAGAS_FAITHFULNESS_ONLY

  # Build ragas SingleTurnSamples from test cases.
  samples = []
  for i, tc in enumerate(test_cases):
    contexts = tc.get("retrieval_context")
    if not contexts:
      logger.warning(f"RAGAS sample {i} has no retrieved_contexts — faithfulness will be NaN/0.0")
    else:
      logger.debug(f"RAGAS sample {i} has {len(contexts)} retrieved context(s)")
    samples.append(
        SingleTurnSample(
            user_input=tc["input"],
            response=tc["actual_output"],
            reference=tc.get("expected_output"),
            retrieved_contexts=contexts,
        )
    )

  try:
    dataset = RagasEvaluationDataset(samples=samples)
    eval_result = ragas_evaluate(dataset, metrics=metrics_to_run, llm=llm)
    scores_df = eval_result.to_pandas()
  except Exception as e:
    logger.warning(
        f"Batch RAGAS evaluation failed ({type(e).__name__}: {e}). "
        "Falling back to per-sample evaluation."
    )
    scores_df = _evaluate_samples_individually(samples, metrics_to_run, llm)

  results = []
  for idx, tc in enumerate(test_cases):
    row = scores_df.iloc[idx]

    if RAGAS_COMBINED in ragas_metric_names:
      # Report each individual metric and an aggregate.
      score_breakdown = {}
      for metric in metrics_to_run:
        metric_name = metric.name
        raw_score = _sanitize_score(row.get(metric_name))
        score_breakdown[metric_name] = raw_score
        results.append({
            "test_index": idx,
            "metric": f"{metric_name} (ragas)",
            "score": raw_score,
            "threshold": threshold,
            "success": raw_score >= threshold,
            "reason": None,
            "cost": None,
        })

      combined_score = (
          sum(score_breakdown.values()) / len(score_breakdown) if score_breakdown else 0.0
      )
      combined_score = _sanitize_score(combined_score)
      results.append({
          "test_index": idx,
          "metric": RAGAS_COMBINED,
          "score": combined_score,
          "threshold": threshold,
          "success": combined_score >= threshold,
          "reason": None,
          "cost": None,
      })

    if RAGAS_FAITHFULNESS in ragas_metric_names and RAGAS_COMBINED not in ragas_metric_names:
      faith_score = _sanitize_score(row.get("faithfulness"))
      results.append({
          "test_index": idx,
          "metric": RAGAS_FAITHFULNESS,
          "score": faith_score,
          "threshold": threshold,
          "success": faith_score >= threshold,
          "reason": None,
          "cost": None,
      })

  return results

def run_ragas_and_merge(
    test_cases: list[dict],
    ragas_metric_names: list[str],
    agent_name: str,
    model: str,
    rag: bool,
) -> list[dict]:
  """Run RAGAS metrics directly and format results to match DeepEval result format.

  Args:
    test_cases: List of dicts with keys: input, actual_output, expected_output, retrieval_context.
    ragas_metric_names: RAGAS metric names to run.
    agent_name: Name of the agent being evaluated.
    model: Model name.
    rag: Whether RAG is enabled.

  Returns:
    List of result dicts matching the format from get_eval_result.
  """
  if not ragas_metric_names:
    return []

  ragas_results = _run_ragas_evaluation(test_cases, ragas_metric_names)

  formatted = []
  for r in ragas_results:
    formatted.append({
        'agent': agent_name,
        'model': model,
        'rag': rag,
        'test_name': f"test_{r['test_index']:03d}",
        'metric': r['metric'],
        'score': r['score'],
        'cost': r['cost'],
        'threshold': r['threshold'],
        'success': r['success'],
        'reason': r['reason'],
    })
  return formatted


def compute_metrics_averages(metric_list):
  """
  Compute the average score for each metric in the list.
  """
  totals = {}
  counters = {}

  for entry in metric_list:
    m = entry['metric']
    s = entry['score']
    totals[m] = totals.get(m, 0.0) + s
    counters[m] = counters.get(m, 0) + 1

  averages = [{'metric': m, 'score': float(f'{totals[m] / counters[m]:.3f}')} for m in totals]
  return averages


if __name__ == '__main__':
  metrics = [
      {'metric': 'accuracy', 'score': 0.8},
      {'metric': 'accuracy', 'score': 0.7},
      {'metric': 'faithfulness', 'score': 0.9},
      {'metric': 'faithfulness', 'score': 0.8},
  ]
  averages = compute_metrics_averages(metrics)
  print(f'Metric averages: {str(averages)}')

def log_metrics_to_dvc(experiment_results: list[dict[str, bool|str|float]], live: Live) -> list[dict[str, Any]]:
  """A utility to log selected metrics to DVC."""
  recorded_results = []
  for result in experiment_results:
    if result["metric"].endswith("(ragas)") and  (not result["metric"].startswith("faithfulness")):
      continue
    recorded_results.append(result)
  
  for result in recorded_results:
    live.log_metric(name=result["metric"], val=result["score"], timestamp=True)

  # Log the average score for each metric to add it to the summary (instead of the default behavior which logs the latest value to the metrics summary)
  average_scores = compute_metrics_averages(recorded_results)
  for average in average_scores:
    live.log_metric(name=average["metric"], val=average["score"], timestamp=True)
    # Also log the average scores in the summary.
    live.summary["metrics"][average["metric"]] = average["score"]
  