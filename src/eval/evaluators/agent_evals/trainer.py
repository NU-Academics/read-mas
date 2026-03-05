"""Trainer to optimize the agents' system prompts using prompt optimization algorithms."""

from loguru import logger
import os

from deepeval.dataset import Golden
from deepeval import evaluate
from deepeval.prompt import Prompt
from deepeval.optimizer import PromptOptimizer
from deepeval.optimizer.configs import AsyncConfig
from deepeval.test_case import LLMTestCase
from dvclive.live import Live

from eval.utils.constants import (
  PROMPT_OPTIMIZER_MODEL
)
from orchestrator import run_agent
from utils.constants import AgentRunMode
from utils.logger import get_run_id
from utils.logger import setup_logging
from eval.utils import (
  get_metrics,
  get_prompt,
  get_eval_agent,
  get_goldens
)

os.environ["DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE"] = "1200" 
os.environ["DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE"] = "240"

TRAIN_RUN_PATH = "runs/train_runs"
class AgentTrainer:
  """This class utilizes DeepEval's prompt optimizer to optimize system prompts of agents."""
  

  def __init__(self, agent_type: str, model: str, rag: bool, experiment: bool):
    
    self.logger = setup_logging(get_run_id(), "eval")

    self._agent_type = agent_type
    self._model = model
    self._rag = rag
    self._experiment = experiment
    self._prompt_to_optimize = get_prompt(self._agent_type)
    self._evaluated_agent = get_eval_agent(self._agent_type, self._model, self._prompt_to_optimize.text_template, self._rag, AgentRunMode.TRAIN)
    self._metrics = get_metrics(self._agent_type, self._rag)
    self._goldens = get_goldens(self._agent_type, self._rag, AgentRunMode.TRAIN)


  async def agent_callback(self, prompt: Prompt, golden: Golden) -> str:
    prompt_text = prompt.text_template
    return await run_agent(golden.input, self._evaluated_agent)


  async def _log_metrics(self, prompt: Prompt, live: Live):
    test_cases = []

    for golden in self._goldens:
      actual_output = await self.agent_callback(prompt, golden)

      test_cases.append(
          LLMTestCase(
              input=golden.input, 
              expected_output=golden.expected_output, 
              actual_output=actual_output,
              retrieval_context=golden.retrieval_context
          )
      )

    results = evaluate(test_cases=test_cases, metrics=self._metrics)

    for test_result in results.test_results:
      scores = [
        m.score
        for m in (test_result.metrics_data or [])
        if getattr(m, "score", None) is not None
      ]
      avg_score = sum(scores) / len(scores) if scores else None
      logger.debug(f"Average optimization score is: {avg_score}")
      live.log_metric(test_result.name, avg_score)


  async def train_agent(self):
    """Train/optimize a READ-MAS agent using prompt optimization algorithms.
    When not running as a DVC experiment, results are not logged to DVC.
    """
    logger.info(f"Optimizing {self._agent_type}'s system prompt.")
    
    async_config = AsyncConfig(
      run_async=True,
      throttle_value=1,
      max_concurrent = 32
    )
    optimizer = PromptOptimizer(
        metrics=self._metrics, model_callback=self.agent_callback, optimizer_model=PROMPT_OPTIMIZER_MODEL, 
        async_config=async_config
    )

    if(not self._experiment):
      optimized_prompt = optimizer.optimize(prompt=self._prompt_to_optimize, goldens=self._goldens)
      logger.debug(f"Original prompt: {self._prompt_to_optimize.text_template}")
      logger.debug(f"Optimized prompt: {optimized_prompt.text_template}")
      return self._prompt_to_optimize.text_template, optimized_prompt.text_template

    with Live(TRAIN_RUN_PATH, report="notebook") as live:
      optimized_prompt = optimizer.optimize(prompt=self._prompt_to_optimize, goldens=self._goldens)
      logger.debug(f"Original prompt: {self._prompt_to_optimize.text_template}")
      logger.debug(f"Optimized prompt: {optimized_prompt.text_template}")

      if not live.summary:
        live.summary = {"prompts": {}, "metrics": []}

      live.summary["prompts"]["original"] = self._prompt_to_optimize.text_template
      live.summary["prompts"]["optimized"] = optimized_prompt.text_template
      live.summary["metrics"] = [m.__name__ for m in self._metrics]

      await self._log_metrics(optimized_prompt, live)
    
    logger.debug(f"Final optimized prompt: {optimized_prompt.text_template}")
    return self._prompt_to_optimize.text_template, optimized_prompt.text_template
