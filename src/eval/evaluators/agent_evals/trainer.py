"""Trainer to optimize the agents' system prompts using prompt optimization algorithms."""

import json
from dotenv import load_dotenv
from loguru import logger

from deepeval.dataset import Golden
from deepeval import evaluate
from deepeval.prompt import Prompt
from deepeval.optimizer import PromptOptimizer
from deepeval.optimizer.configs import AsyncConfig
from deepeval.test_case import LLMTestCase
from dvclive.live import Live

from orchestrator import run_agent
from utils.constants import AgentRunMode, ExecMode
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
from eval.utils.constants import PROMPT_OPTIMIZER_MODEL

TRAIN_RUN_PATH = "runs/train_runs"

load_dotenv()

class AgentTrainer:
  """This class utilizes DeepEval's prompt optimizer to optimize system prompts of agents."""

  def __init__(
      self,
      agent_type: str,
      model: str,
      rag: bool,
      no_opt: bool,
      experiment: bool,
      exec_mode: ExecMode = ExecMode.LOCAL,
  ):
    self._agent_type = agent_type
    self._model = model
    self._rag = rag
    self._no_opt = no_opt
    self._experiment = experiment
    self._exec_mode = exec_mode
    self._prompt_to_optimize = get_prompt(self._agent_type)
    self._evaluated_agent = get_eval_agent(
        self._agent_type,
        self._model,
        self._prompt_to_optimize.text_template,
        self._rag,
        AgentRunMode.TRAIN,
        exec_mode=self._exec_mode,
    )
    self._metrics = get_metrics(self._agent_type)
    self._ragas_metric_names = get_ragas_metric_names(self._agent_type, self._rag)
    self._dataset = get_dataset(self._agent_type, self._rag, AgentRunMode.TRAIN)

  async def agent_callback(
      self, prompt: Prompt, golden: Golden, state_collector: dict = None
  ) -> str:
    prompt_text = prompt.text_template
    eval_agent = get_eval_agent(
        self._agent_type, self._model, prompt_text, self._rag, AgentRunMode.TRAIN,
        exec_mode=self._exec_mode,
    )
    return await run_agent(
        golden.input, eval_agent,
        state_collector=state_collector if self._agent_type == "read_agent" else None,
    )

  async def _collect_metrics(self, prompt: Prompt):
    ragas_test_cases = []

    for golden in self._dataset.goldens:
      state: dict = {}
      actual_output = await self.agent_callback(prompt, golden, state_collector=state)

      self._dataset.test_cases.append(
          LLMTestCase(
              input=golden.input,
              expected_output=golden.expected_output,
              actual_output=actual_output,
              context=golden.context,
              retrieval_context=golden.retrieval_context,
          )
      )

      if self._ragas_metric_names:
        retrieval_context = list(golden.retrieval_context) if golden.retrieval_context else []
        srs = state.get("specifier_output")
        design = state.get("designer_output")
        if srs:
          retrieval_context = [srs] + retrieval_context
        else:
          logger.warning(
              "specifier_output not found in session state — RAGAS context falling back to golden"
              " context only"
          )
        if design:
          design_str = json.dumps(design) if isinstance(design, dict) else str(design)
          retrieval_context = retrieval_context + [design_str]
        ragas_test_cases.append({
            "input": golden.input,
            "actual_output": actual_output,
            "expected_output": golden.expected_output,
            "retrieval_context": retrieval_context or None,
        })

    train_results = evaluate(test_cases=self._dataset.test_cases, metrics=self._metrics)
    results = get_eval_result(train_results, self._evaluated_agent.name, self._model, self._rag)

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

    return results

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

    optimized_prompt = (
        optimizer.optimize(prompt=self._prompt_to_optimize, goldens=self._dataset.goldens)
        if not self._no_opt
        else self._prompt_to_optimize
    )
    training_metrics = await self._collect_metrics(optimized_prompt)

    if self._experiment:
      with Live(TRAIN_RUN_PATH, report="md") as live:
        if not live.summary:
          live.summary = {
              "agent": self._evaluated_agent.name,
              "model": self._model,
              "rag": self._rag,
              "no_opt": self._no_opt,
              "prompts": {},
              "metrics": [],
          }

        live.summary["prompts"]["original"] = self._prompt_to_optimize.text_template
        live.summary["prompts"]["optimized"] = optimized_prompt.text_template
        metric_names = [m.__name__ for m in self._metrics] + self._ragas_metric_names
        live.summary["metrics"] = metric_names

        log_metrics_to_dvc(training_metrics, live)

    logger.debug(f"Original prompt: {self._prompt_to_optimize.text_template}")
    logger.debug(f"Optimized prompt: {optimized_prompt.text_template}")
    logger.debug(f"{AgentRunMode.TRAIN.capitalize()} results: {training_metrics}")
