"""Constants used by the Eval module."""

from typing import Literal
from pathlib import Path

from deepeval.metrics import AnswerRelevancyMetric, ContextualRelevancyMetric, BaseMetric
from deepeval.metrics import FaithfulnessMetric
from deepeval.prompt import Prompt
from single import SingleAgent
from requirement import (CollectorAgent, AnalyzerAgent, SpecifierAgent, RequirementsWrapperAgent)
from design import (DesignerAgent, DocumenterAgent, DesignWrapperAgent)
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

GOLDENS_BASE_PATH = Path("data/goldens")

AGENT_GOLDENS_MAP = {
  "analyzer_agent": GOLDENS_BASE_PATH / "analyzer_agent",
  "collector_agent": GOLDENS_BASE_PATH / "collector_agent",
  "designer_agent": GOLDENS_BASE_PATH / "designer_agent",
  "documenter_agent": GOLDENS_BASE_PATH / "documenter_agent",
  "read_agent": GOLDENS_BASE_PATH / "read_agent",
  "single_agent": GOLDENS_BASE_PATH / "single_agent",
  "specifier_agent": GOLDENS_BASE_PATH / "specifier_agent",
}

AGENT_METRICS_MAP = {
  "analyzer_agent": [AnswerRelevancyMetric()],
  "collector_agent": [AnswerRelevancyMetric()],
  "designer_agent": [AnswerRelevancyMetric()],
  "documenter_agent": [AnswerRelevancyMetric()],
  "read_agent": [AnswerRelevancyMetric()],
  "single_agent": [AnswerRelevancyMetric()],
  "specifier_agent": [AnswerRelevancyMetric()],
}

AGENT_RAG_METRICS_MAP = {
  "analyzer_agent": [AnswerRelevancyMetric(), ContextualRelevancyMetric(), FaithfulnessMetric()],
  "collector_agent": [AnswerRelevancyMetric(), ContextualRelevancyMetric(), FaithfulnessMetric()],
  "designer_agent": [AnswerRelevancyMetric(), ContextualRelevancyMetric(), FaithfulnessMetric()],
  "documenter_agent": [AnswerRelevancyMetric(), ContextualRelevancyMetric(), FaithfulnessMetric()],
  "read_agent": [AnswerRelevancyMetric(), ContextualRelevancyMetric(), FaithfulnessMetric()],
  "single_agent": [AnswerRelevancyMetric(), ContextualRelevancyMetric(), FaithfulnessMetric()],
  "specifier_agent": [AnswerRelevancyMetric(), ContextualRelevancyMetric(), FaithfulnessMetric()],
}

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
