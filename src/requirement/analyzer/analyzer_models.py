from pydantic import BaseModel, Field
from typing import List


class AnalyzerOutputModel(BaseModel):
  useCases: List[str] = Field(
      description=(
          "The list of business use cases as simple string descriptions (e.g., 'Customer registers"
          " for an account'). Each item must be a string, not a structured object."
      )
  )
  domainClasses: str = Field(description="The analysis business classes in the mermaid notation")
  businessRules: List[str] = Field(description="The list of business rules")
  dataModel: str = Field(description="The data model as an ER and DFD in mermaid notation")
  traceability: List[str] = Field(description="The requirements traceability matrix")
  validation: List[str] = Field(description="The requirements validation output")
