from typing import List, Optional

from pydantic import BaseModel, Field


class CollectorOutputModel(BaseModel):
  FRs: Optional[List[str]] = Field(description="The list of functional requirements")
  NFRs: Optional[List[str]] = Field(default=[], description="List of non-functional requirements")
