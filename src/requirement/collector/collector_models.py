from typing import List

from pydantic import Field

from agents import ReadmasBaseModel


class CollectorOutputModel(ReadmasBaseModel):
  FRs: List[str] = Field(default_factory=list, description="The list of functional requirements")

  NFRs: List[str] = Field(default_factory=list, description="List of non-functional requirements")
