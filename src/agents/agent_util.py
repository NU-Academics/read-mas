"""Utility functions common for agents."""

from typing import Union
from google.adk.models.lite_llm import LiteLlm

def get_model_from(llm_model_name: str)->Union[str, LiteLlm]:
  """"Returns the model name as is for Gemini models and a LiteLlm object for others."""
  return llm_model_name if llm_model_name.startswith("Gemini") else LiteLlm(llm_model_name)
