"""Constants for the tools."""

import enum

class OutputType(enum.Enum):
  """Output type for the tools."""
  SRS = "srs"
  DESIGN = "design"
  SEQUENCE_DIAGRAM = "sequence_diagram"
  CLASS_DIAGRAM = "class_diagram"
