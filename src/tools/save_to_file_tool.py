"""Tool to save a string to a file."""

from pathlib import Path
from .constants import OutputType


def _get_output_file_name(output_type: OutputType) -> str:
  """Get the output file name based on the output type.
  
  Args:
    output_type: The agent output type
  """
  
  OUTPUT_FOLDER_MAP = {
      OutputType.SRS: "srs",
      OutputType.DESIGN: "design",
      OutputType.SEQUENCE_DIAGRAM: "sequence_diagram",
      OutputType.CLASS_DIAGRAM: "class_diagram",
  }
  file_path = Path("runs") / "eval" / "outputs" / OUTPUT_FOLDER_MAP[output_type] / output_type + ".md"

  file_path.mkdir(parents=True, exist_ok=True)
  return file_path

def save_to_file(file_content: str, output_type: OutputType) -> str:
  """Save a string to a file."""
  
  file_path = _get_output_file_name(output_type=output_type)
  with open(file_path, "w") as f:
      f.write(file_content)
