"""A benchmarking class to measure READ-MAS agent performance using coding benchmarks: HumanEval and MBPP."""

import resource
import sys
from typing import Optional
from loguru import logger
import json

from dvclive.live import Live
import numpy as np

from eval.utils import (
    get_prompt,
    get_eval_agent,
)
from utils.constants import (
    AgentRunMode,
)

# Monkey‑patch setrlimit and forking for child processes on macOS to enable running evalplus.evaluate and log the results to DVC.
if sys.platform == "darwin":
  import multiprocessing

  multiprocessing.set_start_method('fork', force=True)

  def _noop_setrlimit(resource_id, limits):
    """No-op: setrlimit(RLIMIT_AS/DATA) always fails on macOS when current limit is RLIM_INFINITY."""
    return limits

  resource.setrlimit = _noop_setrlimit

from evalplus.evaluate import evaluate
from evalplus.eval import estimate_pass_at_k


def calculate_pass_at_k(results: dict) -> list[dict]:
  """Compute pass@k and pass@kplus metrics from an evalplus eval_results dict."""
  total = np.array([len(r) for r in results["eval"].values()])
  base_correct = []
  new_correct = []

  for res in results["eval"].values():
    bc = sum([r["base_status"] == "pass" for r in res])
    base_correct.append(bc)
    new_correct.append(
        sum([res[i]["base_status"] == res[i]["plus_status"] == "pass" for i in range(len(res))])
    )
  base_correct = np.array(base_correct)

  metrics = []

  pass_at_k = {
      f"pass@{k}": float(f"{estimate_pass_at_k(total, base_correct, k).mean():.3f}")
      for k in [1, 10, 100]
      if total.min() >= k
  }
  for k, v in pass_at_k.items():
    metrics.append({"metric": k, "score": v})

  pass_at_k_plus = {
      f"pass@{k}plus": float(f"{estimate_pass_at_k(total, np.array(new_correct), k).mean():.3f}")
      for k in [1, 10, 100]
      if (total >= k).all()
  }
  for k, v in pass_at_k_plus.items():
    metrics.append({"metric": k, "score": v})

  return metrics


class _BaseCodingBenchmarker:
  """Shared evalplus evaluation and DVC logging logic."""

  async def _evaluate(self) -> list[dict]:
    evaluate(self._dataset, self._samples_file)

    eval_results_file = self._samples_file.replace(".jsonl", "_eval_results.json")
    with open(eval_results_file, "r") as o:
      results = json.load(o)

    return calculate_pass_at_k(results)

  def _log_to_dvc(self, results: list[dict], summary: dict):
    with Live(self._run_path, report="md") as live:
      if not live.summary:
        live.summary = summary
      live.summary["metrics"] = ["pass@1", "pass@1plus"]
      for result in results:
        live.log_metric(name=result["metric"], val=result["score"])


class CodingBenchmarker(_BaseCodingBenchmarker):
  """This class utilizes the EvalPlus library to benchmark READ-MAS agents using the HumanEval and MBPP metrics."""

  def __init__(
      self,
      run_id: str,
      agent_type: str,
      dataset: str,
      samples_file: str,
      model: Optional[str],
      rag: Optional[bool],
      run_mode: Optional[AgentRunMode] = AgentRunMode.CODE_BENCHMARK,
      experiment: Optional[bool] = False,
  ):

    self._run_id = run_id
    self._agent_type = agent_type
    self._dataset = dataset
    self._samples_file = samples_file
    self._model = model
    self._rag = rag
    self._run_mode = run_mode
    self._experiment = experiment
    self._system_prompt = get_prompt(self._agent_type)
    self._evaluated_agent = get_eval_agent(
        self._agent_type, self._model, self._system_prompt.text_template, self._rag, self._run_mode
    )
    self._run_path = "runs/" + self._run_mode.value + "_runs"

  async def benchmark(self):
    """Run the coding benchmarks against samples created from agent."""
    logger.info(
        f"Benchmarking {self._evaluated_agent.name} agent using the {self._dataset} benchmark."
    )

    results = await self._evaluate()

    if self._experiment:
      self._log_to_dvc(
          results,
          {
              "agent": self._evaluated_agent.name,
              "model": self._model,
              "rag": self._rag,
              "benchmark": self._dataset,
          },
      )

    logger.debug(f"{self._run_mode.name.capitalize()} results: {results}")


class LlmCodingBenchmarker(_BaseCodingBenchmarker):
  """Benchmarks a raw LLM on HumanEval/MBPP without any agent orchestration."""

  def __init__(
      self,
      run_id: str,
      model: str,
      dataset: str,
      samples_file: str,
      experiment: bool = False,
  ):
    self._run_id = run_id
    self._model = model
    self._dataset = dataset
    self._samples_file = samples_file
    self._experiment = experiment
    self._run_mode = AgentRunMode.LLM_BENCHMARK
    self._run_path = "runs/" + AgentRunMode.LLM_BENCHMARK + "_runs"

  async def benchmark(self):
    """Run the coding benchmarks against samples generated directly from the LLM."""
    logger.info(f"Benchmarking {self._model} on {self._dataset}")

    results = await self._evaluate()

    if self._experiment:
      self._log_to_dvc(results, {"model": self._model, "benchmark": self._dataset})

    logger.debug(f"LLM benchmark results: {results}")
