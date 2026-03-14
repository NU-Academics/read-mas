"""Agent evaluator class to evaluate and benchmark READ-MAS agents using custom LLM-as-a-Judge and RAGAS metrics."""

from dotenv import load_dotenv
from typing import Optional
from loguru import logger

from deepeval import evaluate
from deepeval.evaluate.types import EvaluationResult
from deepeval.test_case import LLMTestCase
from dvclive.live import Live

from orchestrator import run_agent
from eval.utils import (compute_metrics_averages, get_metrics, get_prompt, get_eval_agent, get_dataset, get_eval_result)
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
    self._metrics = get_metrics(self._agent_type, self._rag)
    self._dataset = get_dataset(self._agent_type, self._rag, AgentRunMode.EVAL)
    self._run_path = "runs/" + self._run_mode.value + "_runs"

  async def _evaluate(self) -> EvaluationResult:
    """Generate test cases from the goldens and evaluate the agent."""
    for golden in self._dataset.goldens:
      actual_output = await run_agent(golden.input, self._evaluated_agent)

      self._dataset.test_cases.append(
          LLMTestCase(
              input=golden.input,
              expected_output=golden.expected_output,
              actual_output=actual_output,
              context=golden.context,
              retrieval_context=golden.retrieval_context,
          )
      )
    
    return evaluate(test_cases=self._dataset.test_cases, metrics=self._metrics)

  async def eval_agent(self):
    """Evaluate a READ-MAS agent using LLM-as-a-Judge.
    When not running as a DVC experiment, results are not logged to DVC.
    """
    logger.info(f"Evaluating {self._evaluated_agent.name} agent.")

    eval_results = await self._evaluate()

    results = get_eval_result(eval_results, self._evaluated_agent.name, self._model, self._rag)

    if self._experiment:
      with Live(self._run_path, report="md") as live:

        if not live.summary:
          live.summary = {
              "agent": self._evaluated_agent.name,
              "model": self._model,
              "rag": self._rag,
              "metrics": [],
          }

        live.summary["metrics"] = [m.__name__ for m in self._metrics]

        for result in results:
          live.log_metric(name=result["metric"], val=result["score"], timestamp=True)
          
        average_scores = compute_metrics_averages(results)
        for average in average_scores:
          live.log_metric(name=average["metric"], val=average["score"], timestamp=True)


    logger.debug(f"{self._run_mode.name.capitalize()} results: {results}")
