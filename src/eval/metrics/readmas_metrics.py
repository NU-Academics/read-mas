"""Metrics for the READ-MAS system."""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from utils.constants import EVALUATION_MODEL

architecture_soundness = GEval(
  name="ArchitectureSoundness",
  criteria="The design reflects a separation of concerns between its components and is feasible for implementation.",
  model=EVALUATION_MODEL,
  evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT]
)