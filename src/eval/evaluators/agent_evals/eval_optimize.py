"""Evaluator to optimize the agent."""

import asyncio
import json
from typing import Optional
import yaml

from deepeval.dataset import Golden
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, ContextualRelevancyMetric
from deepeval.metrics.ragas import RAGASFaithfulnessMetric
from deepeval.prompt import Prompt
from deepeval.optimizer import PromptOptimizer
from deepeval.test_case import LLMTestCase
from dvclive import Live
from google.adk.agents import BaseAgent
from prompt_templates import (
    SINGLE_AGENT_SYSTEM_PROMPT,
    COLLECTOR_AGENT_SYSTEM_PROMPT,
    ANALYZER_AGENT_SYSTEM_PROMPT,
    SPECIFIER_AGENT_SYSTEM_PROMPT,
    RE_AGENT_SYSTEM_PROMPT,
    DESIGNER_AGENT_SYSTEM_PROMPT,
    DOCUMENTER_AGENT_SYSTEM_PROMPT,
    DESIGN_AGENT_SYSTEM_PROMPT,
)
from single import SingleAgent
from requirement import (CollectorAgent, AnalyzerAgent, SpecifierAgent, RequirementsWrapperAgent)
from design import (DesignerAgent, DocumenterAgent, DesignWrapperAgent)
from orchestrator import run_agent
from utils import DEFAULT_MODEL_NAME
from utils.constants import AgentRunMode
from utils.logger import setup_logging

# logger = setup_logging(__name__)

AGENT_PROMPTS = {
    "single_agent": Prompt(text_template=SINGLE_AGENT_SYSTEM_PROMPT),
    "collector_agent": Prompt(text_template=COLLECTOR_AGENT_SYSTEM_PROMPT),
    "analyzer_agent": Prompt(text_template=ANALYZER_AGENT_SYSTEM_PROMPT),
    "specifier_agent": Prompt(text_template=SPECIFIER_AGENT_SYSTEM_PROMPT),
    "re_agent": Prompt(text_template=RE_AGENT_SYSTEM_PROMPT),
    "designer_agent": Prompt(text_template=DESIGNER_AGENT_SYSTEM_PROMPT),
    "documenter_agent": Prompt(text_template=DOCUMENTER_AGENT_SYSTEM_PROMPT),
    "design_agent": Prompt(text_template=DESIGN_AGENT_SYSTEM_PROMPT),
}

AGENT_REGISTRY = {
    "single_agent": SingleAgent,
    "collector_agent": CollectorAgent,
    "analyzer_agent": AnalyzerAgent,
    "specifier_agent": SpecifierAgent,
    "re_agent": RequirementsWrapperAgent,
    "designer_agent": DesignerAgent,
    "documenter_agent": DocumenterAgent,
    "design_agent": DesignWrapperAgent,
}

agent_name = None
llm_model_name = None
evaluated_agent = None
rag = False
prompt_to_optimize = None
goldens = None
metrics = [AnswerRelevancyMetric()]


def _get_prompt(agent_name: str) -> Prompt:
  return AGENT_PROMPTS[agent_name]


def _get_eval_agent(prompt: str) -> BaseAgent:
  agent_type = AGENT_REGISTRY[agent_name]
  return agent_type(llm_model_name, prompt, AgentRunMode.EVAL, rag).get_agent()


async def agent_callback(prompt: Prompt, golden: Golden) -> str:
  prompt = prompt.text_template
  evaluated_agent = _get_eval_agent(prompt)
  return await run_agent(golden.input, evaluated_agent)


def _get_goldens() -> list[Golden]:
  with open("data/goldens/20260213_234211.json", "r") as jf:
    goldens_list = json.load(jf)

  return [Golden.model_validate(g) for g in goldens_list]


async def _log_metrics(prompt: Prompt, live: Live):
  test_cases = []

  for golden in goldens:
    actual_output = await agent_callback(prompt, golden)

    test_cases.append(
        LLMTestCase(
            input=golden.input, expected_output=golden.expected_output, actual_output=actual_output
        )
    )

  results = evaluate(test_cases=test_cases, metrics=metrics)

  for test_result in results.test_results:
    scores = [m.score for m in test_result.metrics_data]
    avg_score = sum(scores) / len(scores)
    live.log_metric(test_result.name, avg_score)


async def _optimize_agent(live: Live):
  optimizer = PromptOptimizer(
      metrics=metrics, model_callback=agent_callback, optimizer_model="gpt-5-nano"
  )
  optimized_prompt = optimizer.optimize(prompt=prompt_to_optimize, goldens=goldens)

  if not live.summary:
    live.summary = {"prompts": {}, "metrics": []}

  live.summary["prompts"]["original"] = prompt_to_optimize.text_template
  live.summary["prompts"]["optimized"] = optimized_prompt.text_template
  live.summary["metrics"] = [m.__name__ for m in metrics]

  await _log_metrics(optimized_prompt, live)


async def main():
  with Live(EVAL_PATH) as live:
    await _optimize_agent(live)


if __name__ == "__main__":
  EVAL_PATH = "evals"

  params = yaml.safe_load(open("params.yaml"))["eval"]
  agent_name = params["agent_name"]
  llm_model_name = params["llm_model_name"]
  rag = params["rag"]
  prompt_to_optimize = _get_prompt(params["agent_name"])
  evaluated_agent = _get_eval_agent(prompt_to_optimize.text_template)
  goldens = _get_goldens()

  asyncio.run(main())
