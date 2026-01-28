from pydantic import BaseModel, Field
from typing import List


class DesignerOutputModel(BaseModel):
  systemArchitecture: str = Field(description=("The system architecture with textual specification and architecture diagrams using the mermaid notation."))
  fileStructure: str = Field(description="The file structure for the designed system.")
  componentDesign: str = Field(description="Component design consisting of one or more class diagrams and one or more sequence diagrams drawn using the mermaid notation.")
