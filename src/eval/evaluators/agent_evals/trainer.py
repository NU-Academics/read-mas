"""Trainer to optimize the agents' system prompts using prompt optimization algorithms."""

from loguru import logger

from deepeval.dataset import Golden
from deepeval import evaluate
from deepeval.prompt import Prompt
from deepeval.optimizer import PromptOptimizer
from deepeval.optimizer.configs import AsyncConfig
from deepeval.test_case import LLMTestCase
from dvclive.live import Live

from orchestrator import run_agent
from utils.constants import AgentRunMode
from eval.utils import (
    compute_metrics_averages,
    get_metrics,
    get_prompt,
    get_eval_agent,
    get_dataset,
    get_eval_result,
)
from eval.utils.constants import PROMPT_OPTIMIZER_MODEL

TRAIN_RUN_PATH = "runs/train_runs"


class AgentTrainer:
  """This class utilizes DeepEval's prompt optimizer to optimize system prompts of agents."""

  def __init__(self, agent_type: str, model: str, rag: bool, experiment: bool):
    self._agent_type = agent_type
    self._model = model
    self._rag = rag
    self._experiment = experiment
    self._prompt_to_optimize = get_prompt(self._agent_type)
    self._evaluated_agent = get_eval_agent(
        self._agent_type,
        self._model,
        self._prompt_to_optimize.text_template,
        self._rag,
        AgentRunMode.TRAIN,
    )
    self._metrics = get_metrics(self._agent_type, self._rag)
    self._dataset = get_dataset(self._agent_type, self._rag, AgentRunMode.TRAIN)

  async def agent_callback(self, prompt: Prompt, golden: Golden) -> str:
    prompt_text = prompt.text_template
    eval_agent = get_eval_agent(
        self._agent_type, self._model, prompt_text, self._rag, AgentRunMode.TRAIN
    )
    return await run_agent(golden.input, eval_agent)

  async def _collect_metrics(self, prompt: Prompt):
    for golden in self._dataset.goldens:
      actual_output = await self.agent_callback(prompt, golden)

      self._dataset.test_cases.append(
          LLMTestCase(
              input=golden.input,
              expected_output=golden.expected_output,
              actual_output=actual_output,
              context=golden.context,
              retrieval_context=golden.retrieval_context,
          )
      )

    train_results = evaluate(test_cases=self._dataset.test_cases, metrics=self._metrics)
    return get_eval_result(train_results, self._evaluated_agent.name, self._model, self._rag)

  async def train_agent(self):
    """Train/optimize a READ-MAS agent using prompt optimization algorithms.
    When not running as a DVC experiment, results are not logged to DVC.
    """
    logger.info(f"Optimizing {self._agent_type}'s system prompt.")

    async_config = AsyncConfig(run_async=True, throttle_value=1, max_concurrent=32)
    optimizer = PromptOptimizer(
        metrics=self._metrics,
        model_callback=self.agent_callback,
        optimizer_model=PROMPT_OPTIMIZER_MODEL,
        async_config=async_config,
    )

    optimized_prompt = optimizer.optimize(
        prompt=self._prompt_to_optimize, goldens=self._dataset.goldens
    )
    optimized_metrics = await self._collect_metrics(optimized_prompt)

    if self._experiment:
      with Live(TRAIN_RUN_PATH, report="md") as live:
        if not live.summary:
          live.summary = {
              "agent": self._evaluated_agent.name,
              "model": self._model,
              "rag": self._rag,
              "prompts": {},
              "metrics": [],
          }

        live.summary["prompts"]["original"] = self._prompt_to_optimize.text_template
        live.summary["prompts"]["optimized"] = optimized_prompt.text_template
        live.summary["metrics"] = [m.__name__ for m in self._metrics]

        for result in optimized_metrics:
          live.log_metric(name=result["metric"], val=result["score"], timestamp=True)

        # Log the average score for each metric to add it to the summary (instead of the default behavior which logs the latest value to the metrics summary)
        average_scores = compute_metrics_averages(optimized_metrics)
        for average in average_scores:
          live.log_metric(name=average["metric"], val=average["score"], timestamp=True)

    logger.debug(f"Original prompt: {self._prompt_to_optimize.text_template}")
    logger.debug(f"Optimized prompt: {optimized_prompt.text_template}")
    logger.debug(f"{AgentRunMode.TRAIN.capitalize()} results: {optimized_metrics}")
