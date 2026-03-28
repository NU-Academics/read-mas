"""Agent evaluator class to evaluate and benchmark READ-MAS agents using custom LLM-as-a-Judge and RAGAS metrics."""

from dotenv import load_dotenv
from typing import Optional
from loguru import logger

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig
from deepeval.evaluate.types import EvaluationResult
from deepeval.test_case import LLMTestCase
from dvclive.live import Live

from orchestrator import run_agent
from eval.utils import (
    get_metrics,
    get_ragas_metric_names,
    get_prompt,
    get_eval_agent,
    get_dataset,
    get_eval_result,
    log_metrics_to_dvc,
    run_ragas_and_merge,
)
from utils.constants import (
    AgentRunMode,
)

load_dotenv()


class AgentEvaluator:
  """This class utilizes DeepEval's GEval framework to evaluate agents using LLM-as-a-Judge."""

  def __init__(
      self,
      agent_type: str,
      model: Optional[str],
      rag: Optional[bool],
      run_mode: Optional[AgentRunMode] = AgentRunMode.EVAL,
      experiment: Optional[bool] = False,
  ):
    self._agent_type = agent_type
    self._model = model
    self._rag = rag
    self._run_mode = run_mode
    self._experiment = experiment
    self._system_prompt = get_prompt(self._agent_type)
    self._evaluated_agent = get_eval_agent(
        self._agent_type, self._model, self._system_prompt.text_template, self._rag, self._run_mode
    )
    self._metrics = get_metrics(self._agent_type)
    self._ragas_metric_names = get_ragas_metric_names(self._agent_type, self._rag)
    self._dataset = get_dataset(self._agent_type, self._rag, AgentRunMode.EVAL)
    self._run_path = "runs/" + self._run_mode.value + "_runs"

  async def _run_single_golden(self, golden):
    """Run the agent on a single golden and return test case + ragas data."""
    actual_output = await run_agent(golden.input, self._evaluated_agent, run_mode=self._run_mode)

    test_case = LLMTestCase(
        input=golden.input,
        expected_output=golden.expected_output,
        actual_output=actual_output,
        context=golden.context,
        retrieval_context=golden.retrieval_context,
    )

    ragas_data = None
    if self._ragas_metric_names:
      ragas_data = {
          "input": golden.input,
          "actual_output": actual_output,
          "expected_output": golden.expected_output,
          "retrieval_context": golden.retrieval_context,
      }

    return test_case, ragas_data

  async def _evaluate(self) -> tuple[EvaluationResult, list[dict]]:
    """Generate test cases from the goldens and evaluate the agent."""
    ragas_test_cases = []
    for golden in self._dataset.goldens:
      test_case, ragas_data = await self._run_single_golden(golden)
      self._dataset.test_cases.append(test_case)
      if ragas_data is not None:
        ragas_test_cases.append(ragas_data)

    deepeval_result = evaluate(
        test_cases=self._dataset.test_cases,
        metrics=self._metrics,
        async_config=AsyncConfig(run_async=False),
    )
    return deepeval_result, ragas_test_cases

  async def eval_agent(self):
    """Evaluate a READ-MAS agent using LLM-as-a-Judge.
    When not running as a DVC experiment, results are not logged to DVC.
    """
    logger.info(f"Evaluating {self._evaluated_agent.name} agent.")

    eval_results, ragas_test_cases = await self._evaluate()

    results = get_eval_result(eval_results, self._evaluated_agent.name, self._model, self._rag)

    # Run RAGAS metrics directly via the ragas library and merge results.
    if self._ragas_metric_names:
      ragas_results = run_ragas_and_merge(
          ragas_test_cases,
          self._ragas_metric_names,
          self._evaluated_agent.name,
          self._model,
          self._rag,
      )
      results.extend(ragas_results)

    if self._experiment:
      with Live(self._run_path, report="md") as live:

        if not live.summary:
          live.summary = {
              "agent": self._evaluated_agent.name,
              "model": self._model,
              "rag": self._rag,
              "metrics": [],
          }

        metric_names = [m.__name__ for m in self._metrics] + self._ragas_metric_names
        live.summary["metrics"] = metric_names

        log_metrics_to_dvc(results, live)

    logger.debug(f"{self._run_mode.name.capitalize()} results: {results}")
