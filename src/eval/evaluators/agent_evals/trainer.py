"""Trainer to optimize the agents' system prompts using prompt optimization algorithms."""

import json
from typing import Optional
from loguru import logger
import os

from deepeval.dataset import Golden
from deepeval import evaluate
from deepeval.metrics import BaseMetric
from deepeval.prompt import Prompt
from deepeval.optimizer import PromptOptimizer
from deepeval.optimizer.configs import AsyncConfig
from deepeval.test_case import LLMTestCase
from dvclive.live import Live
from google.adk.agents import BaseAgent

from eval.utils.constants import (
  AGENT_GOLDENS_MAP,
  AGENT_METRICS_MAP,
  AGENT_RAG_METRICS_MAP,
  AGENT_PROMPTS,
  AGENT_REGISTRY,
)
from rag import retrieve_requirements
from orchestrator import run_agent
from utils import DEFAULT_MODEL_NAME
from utils.constants import AgentRunMode
from utils.logger import get_run_id
from utils.logger import setup_logging

PROMPT_OPTIMIZER_MODEL = "gpt-5-nano"

os.environ["DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE"] = "1200" 
os.environ["DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE"] = "240"

class AgentTrainer:
  """This class utilizes DeepEval's prompt optimizer to optimize system prompts of agents."""
  
  EVAL_PATH = "runs/train_runs"

  def __init__(self, agent_name: str, model: str, rag: bool, experiment: bool):
    
    self.logger = setup_logging(get_run_id(), "eval")

    # params = yaml.safe_load(open("params.yaml"))["eval"]
    self._agent_name = agent_name
    self._model = model
    self._rag = rag
    self._experiment = experiment
    self._prompt_to_optimize = self._get_prompt(self._agent_name)
    self._evaluated_agent = self._get_eval_agent(self._prompt_to_optimize.text_template)
    self._metrics = self._get_metrics(self._agent_name, self._rag)
    self._goldens = self._get_goldens(self._agent_name, self._rag)


  def _get_metrics(self, agent_name: str, rag: bool = False) -> list[BaseMetric]:
    if rag:
      return AGENT_RAG_METRICS_MAP[agent_name]
      
    return AGENT_METRICS_MAP[agent_name]


  def _get_prompt(self, agent_name: str) -> Prompt:
    return AGENT_PROMPTS[agent_name]


  def _get_eval_agent(self, prompt: Optional[str]) -> BaseAgent:
    agent_type = AGENT_REGISTRY[self._agent_name]
    return agent_type(self._model, prompt, AgentRunMode.EVAL, self._rag).get_agent()


  async def agent_callback(self, prompt: Prompt, golden: Golden) -> str:
    prompt_text = prompt.text_template
    evaluated_agent = self._get_eval_agent(prompt_text)
    return await run_agent(golden.input, evaluated_agent)


  def _get_goldens(self, agent_name: str, rag: bool) -> list[Golden]:
    golden_path = AGENT_GOLDENS_MAP[agent_name] / "train.json"
    with open(golden_path, "r") as jf:
      goldens_list = json.load(jf)

    goldens = [Golden.model_validate(g) for g in goldens_list]
    
    if rag:
      for golden in goldens:
        retrieval_context = retrieve_requirements(golden.input)
        golden.retrieval_context = retrieval_context or None
        
    return goldens



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
    logger.info(f"Optimizing {self._agent_name}'s system prompt.")
    
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

    with Live(EVAL_PATH, report="notebook") as live:
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
