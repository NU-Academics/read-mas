from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class AnalyzerOutputModel(BaseModel):
  # NOTE: We keep this schema permissive because some LLMs occasionally omit fields
  # or return the wrong primitive type (e.g., a string where a list is expected).
  # Downstream agents (specifier/design) can still proceed with best-effort outputs.
  useCases: List[str] = Field(
      default_factory=list,
      description=(
          "The list of business use cases as simple string descriptions (e.g., 'Customer registers"
          " for an account'). Each item must be a string, not a structured object."
      ),
  )
  domainClasses: str = Field(
      default="",
      description="The analysis business classes in the mermaid notation",
  )
  businessRules: List[str] = Field(default_factory=list, description="The list of business rules")
  dataModel: str = Field(
      default="",
      description="The data model as an ER and DFD in mermaid notation",
  )
  traceability: List[str] = Field(
      default_factory=list, description="The requirements traceability matrix"
  )
  validation: List[str] = Field(
      default_factory=list, description="The requirements validation output"
  )

  @field_validator("useCases", "businessRules", "traceability", "validation", mode="before")
  @classmethod
  def _coerce_str_to_list(cls, v):
    """
    Some models occasionally return list-like fields as a single string
    (e.g. 'FR1→UC1; FR2→UC2; ...' or newline-separated bullets).
    Coerce that into List[str] so downstream agents (specifier) don't fail input validation.
    """
    if v is None:
      return []
    if isinstance(v, list):
      return v
    # Occasionally the model returns a structured object for a list field; stringify it.
    if isinstance(v, dict):
      return [str(v)]
    if isinstance(v, str):
      text = v.strip()
      if not text:
        return []
      # Prefer splitting on newlines; fall back to semicolons if it's a single-line summary.
      if "\n" in text:
        parts = [p.strip(" \t-•") for p in text.splitlines()]
      else:
        parts = [p.strip() for p in text.split(";")]
      return [p for p in parts if p]
    return v

  @field_validator("domainClasses", "dataModel", mode="before")
  @classmethod
  def _coerce_to_str(cls, v):
    """
    Some models return diagrams as lists (lines) or null.
    Coerce into a single string.
    """
    if v is None:
      return ""
    if isinstance(v, str):
      return v
    if isinstance(v, list):
      return "\n".join(str(x) for x in v)
    return str(v)
