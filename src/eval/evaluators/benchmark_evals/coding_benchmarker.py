"""A benchmarking class to measure READ-MAS agent performance using coding benchmarks: HumanEval and MBPP."""

from typing import Optional
from loguru import logger
import json

from dvclive.live import Live
from evalplus.evaluate import evaluate
from evalplus.eval import estimate_pass_at_k
import numpy as np

from eval.utils import (
    get_prompt,
    get_eval_agent,
)
from utils.constants import (
    AgentRunMode,
)


class CodingBenchmarker:
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

  def _calculate_pass_at_k(self, results: list[dict]):
    """Adapted from EvalPlus since there is no way to programmatically obtain the scores."""
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

    results = []

    pass_at_k = {
        f"pass@{k}": float(f"{estimate_pass_at_k(total, base_correct, k).mean():.3f}")
        for k in [1, 10, 100]
        if total.min() >= k
    }

    for k, v in pass_at_k.items():
      results.append({"metric": k, "score": v})

    pass_at_k_plus = {
        f"pass@{k}plus": float(f"{estimate_pass_at_k(total, np.array(new_correct), k).mean():.3f}")
        for k in [1, 10, 100]
        if (total >= k).all()
    }

    for k, v in pass_at_k_plus.items():
      results.append({"metric": k, "score": v})

    return results

  async def _evaluate(self):
    evaluate(self._dataset, self._samples_file)

    eval_results_file = self._samples_file.replace(".jsonl", "_eval_results.json")
    with open(eval_results_file, "r") as o:
      results = json.load(o)

    return self._calculate_pass_at_k(results)

  async def benchmark(self):
    """Run the coding benchmarks against samples created from agent."""
    logger.info(
        f"Benchmarking {self._evaluated_agent.name} agent using the {self._dataset} benchmark."
    )

    results = await self._evaluate()

    if self._experiment:
      with Live(self._run_path, report="notebook") as live:

        if not live.summary:
          live.summary = {
              "agent": self._evaluated_agent.name,
              "model": self._model,
              "rag": self._rag,
              "benchmark": self._dataset,
              "metrics": [],
          }

        live.summary["metrics"] = ["pass@1", "pass@1plus"]

        for result in results:
          live.log_metric(name=result["metric"], val=result["score"])

    logger.debug(f"{self._run_mode.name.capitalize()} results: {results}")
