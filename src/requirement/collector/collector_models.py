from typing import List

from pydantic import BaseModel, Field


class CollectorOutputModel(BaseModel):
  FRs: List[str] = Field(description="The list of functional requirements")
  NFRs: List[str] = Field(description="List of non-functional requirements")
