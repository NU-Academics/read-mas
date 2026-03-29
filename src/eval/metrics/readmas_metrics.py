"""Metrics for the READ-MAS system."""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from deepeval.metrics import HallucinationMetric
from ragas.metrics import (
    faithfulness as ragas_faithfulness_metric,
    context_precision,
    context_recall,
    ContextEntityRecall,
    ResponseRelevancy,
)

from utils.constants import EVALUATION_MODEL

# RAGAS metric names used in the metrics maps to identify which RAGAS metrics to run.
RAGAS_FAITHFULNESS = "RAGASFaithfulness"
RAGAS_COMBINED = "RAGAS"

# The individual RAGAS metrics that make up the combined RAGAS score.
RAGAS_ALL_METRICS = [
    context_precision,
    context_recall,
    ContextEntityRecall(),
    ResponseRelevancy(),
    ragas_faithfulness_metric,
]

RAGAS_FAITHFULNESS_ONLY = [ragas_faithfulness_metric]

# End-to-end metric for single and read_wrapper agents.
design_accuracy = GEval(
    name="DesignAccuracy",
    criteria=(
        "- Completeness: The design addresses the system's requirements.   - Modularity: The"
        " system architecture reflects a separation of concerns between its components and is"
        " feasible for implementation.   - Best Practices: The architecture and design adhere to"
        " industry best practices.   - Project Definition: The file structure aligns with the"
        " design modularity and the language best practices.   - Component Validity: The class and"
        " sequence diagrams have the right complexity for the system and are valid mermaid"
        " diagrams."
    ),
    model=EVALUATION_MODEL,
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
        LLMTestCaseParams.CONTEXT,
    ],
)

# DeepEval content quality and agentic metrics useful to validate multiple agents
hallucination = HallucinationMetric(model=EVALUATION_MODEL)

# Collector Agent metrics
requirements_accuracy = GEval(
    name="RequirementsAccuracy",
    criteria=(
        "- Completeness: The agent captures the functional (FR) and non-functional (NFR)"
        " requirements for the requested system.   - Classification Accuracy: The agent is precise"
        " in classifying the requirements into FR and NFR.   - Requirement Quality: The agent presents requirements without duplication, clear expression, and avoiding statements that imply more than one intent."
        "  - Consistency: The agent collects requirements without conflicts with each other."
    ),
    model=EVALUATION_MODEL,
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
        LLMTestCaseParams.CONTEXT,
    ],
)

# Analyzer Agent metrics
analysis_accuracy = GEval(
    name="AnalysisAccuracy",
    criteria=(
        "- Use Case Coverage: The use cases cover the FRs in the requirements input.   - Domain"
        " Model Fitness: The domain model captures the major concepts in the system and creates"
        " valid mermaid diagrams.   - Business Rules Accuracy: The business rules accurately"
        " represent the behavior of the system.   - Data Model: The data model extracts"
        " representative entities and depicts their relationships.   - Traceability and Validity:"
        " The analysis entities are traceable to the FRs and NRFs and the validation confirms the"
        " validity of the analysis results."
    ),
    model=EVALUATION_MODEL,
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
        LLMTestCaseParams.CONTEXT,
    ],
)

# Specifier Agent metrics
specification_accuracy = GEval(
    name="SpecificationAccuracy",
    criteria=(
        "- Completeness: The SRS documents all the analysis and collector artifacts.   -"
        " Compliance: The SRS is complete and adheres to the IEEE-830 documentation standard.   -"
        " Consistency: The SRS sections are consistent among themselves and do not introduce"
        " ambiguities."
    ),
    model=EVALUATION_MODEL,
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
        LLMTestCaseParams.CONTEXT,
    ],
)

# Designer Agent metrics
designer_accuracy = GEval(
    name="DesignerAccuracy",
    criteria=(
        "- Requirements Coverage: The design addresses all the requirements in the SRS.   -"
        " Architectural Soundness: The system architecture follows community best practices with"
        " modular, maintainable, and feasible design.   - Component Design: The components of the"
        " system follow the SOLID principle and show the right level of cohesion in and decoupling"
        " among the components.   - File Structure: The file structure is appropriate to the"
        " problem domain and selected technology stack.  - Diagram Validity: The class and sequence"
        " diagrams produce valid mermaid diagrams."
    ),
    model=EVALUATION_MODEL,
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
        LLMTestCaseParams.CONTEXT,
    ],
)

# Documenter Agent metrics
design_document_accuracy = GEval(
    name="DesignDocumentAccuracy",
    criteria=(
        "- Completeness: The design document includes all the sections in the design document"
        " template.   - Compliance: The design document includes the architecture and design"
        " elements in the designer output.   - Traceability: The design is traceable to the SRS."
    ),
    model=EVALUATION_MODEL,
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
        LLMTestCaseParams.CONTEXT,
    ],
)
