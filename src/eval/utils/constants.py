"""Constants used by the Eval module."""

from pathlib import Path

from deepeval.prompt import Prompt

from single import SingleAgent
from requirement import (CollectorAgent, AnalyzerAgent, SpecifierAgent, RequirementsWrapperAgent)
from design import (DesignerAgent, DocumenterAgent, DesignWrapperAgent)
from orchestrator import ReadWrapperAgent
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
from eval.metrics import (
    analysis_accuracy,
    design_accuracy,
    designer_accuracy,
    design_document_accuracy,
    hallucination,
    requirements_accuracy,
    specification_accuracy,
    RAGAS_FAITHFULNESS,
    RAGAS_COMBINED,
)

PROMPT_OPTIMIZER_MODEL = "gpt-5-mini"

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

# DeepEval metrics (run via deepeval.evaluate)
AGENT_METRICS_MAP = {
    "analyzer_agent": [analysis_accuracy, hallucination],
    "collector_agent": [requirements_accuracy, hallucination],
    "designer_agent": [designer_accuracy, hallucination],
    "documenter_agent": [design_document_accuracy, hallucination],
    "read_agent": [design_accuracy],
    "single_agent": [design_accuracy],
    "specifier_agent": [specification_accuracy, hallucination],
}

AGENT_RAGAS_METRICS_MAP = {
    "collector_agent": [RAGAS_COMBINED],
    "read_agent": [RAGAS_COMBINED],
    "single_agent": [RAGAS_COMBINED],
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
    "read_agent": Prompt(text_template=None)
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
    "read_agent": ReadWrapperAgent,
}
