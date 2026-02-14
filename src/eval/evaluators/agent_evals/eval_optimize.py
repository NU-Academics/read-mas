"""Evaluator to optimize the agent."""

import asyncio
import json
from typing import Optional
import yaml

from deepeval.dataset import Golden
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.prompt import Prompt
from deepeval.optimizer import PromptOptimizer
from dvclive import Live
from google.adk.agents import BaseAgent
from prompt_templates import (SINGLE_AGENT_SYSTEM_PROMPT, COLLECTOR_AGENT_SYSTEM_PROMPT, ANALYZER_AGENT_SYSTEM_PROMPT, SPECIFIER_AGENT_SYSTEM_PROMPT, RE_AGENT_SYSTEM_PROMPT, DESIGNER_AGENT_SYSTEM_PROMPT, DOCUMENTER_AGENT_SYSTEM_PROMPT, DESIGN_AGENT_SYSTEM_PROMPT)
from single import SingleAgent
from requirement import (CollectorAgent, AnalyzerAgent, SpecifierAgent, RequirementsWrapperAgent)
from design import (DesignerAgent, DocumenterAgent, DesignWrapperAgent)
from orchestrator.orchestrator import run_agent
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

evaluated_agent = None
prompt_to_optimize = AGENT_PROMPTS["single_agent"]

def _get_prompt(agent_name: str) -> Prompt:
  return AGENT_PROMPTS[agent_name]

def _get_eval_agent(agent_name: str, llm_model_name: Optional[str] = DEFAULT_MODEL_NAME, rag: Optional[bool] = False) -> BaseAgent:
  agent_type = AGENT_REGISTRY[agent_name]
  return agent_type(llm_model_name, AgentRunMode.EVAL, rag).get_agent() 

async def agent_callback(prompt: Prompt, golden: Golden) -> str:
  return await run_agent(golden.input, evaluated_agent)

def _get_goldens() -> list[Golden]:
  with open("data/goldens/20260213_234211.json", "r") as jf:
    goldens_list= json.load(jf)
    
  return [Golden.model_validate(g) for g in goldens_list]
  
async def _optimize_agent(agent_name:str, llm_model_name: str, rag: bool, live: Live):
  prompt = _get_prompt(agent_name)
  global evaluated_agent 
  evaluated_agent = _get_eval_agent(agent_name, llm_model_name, rag)
  metrics = [AnswerRelevancyMetric()]
  goldens = _get_goldens()
  optimizer = PromptOptimizer(metrics=metrics, model_callback=agent_callback, optimizer_model="gpt-5-nano")
  optimized_prompt = optimizer.optimize(
      prompt=prompt,
      goldens=goldens
  )
  
  optimization_results = {
      "original_prompt": prompt.text_template,
      "optimized_prompt": optimized_prompt.text_template,
      "optimization_report": optimizer.optimization_report.__dict__
  }
  
  with open("evals/prompt_optimization_report.json", "w") as f:
      json.dump(optimization_results, f, indent=2)

async def main():
  EVAL_PATH = "evals"
  
  params = yaml.safe_load(open("params.yaml"))["eval"]
  
  with Live(EVAL_PATH) as live:
    await _optimize_agent(params["agent_name"], params["llm_model_name"], params["rag"], live)
  
if __name__ == "__main__":
  asyncio.run(main())