"""Utility functions common for agents."""

from typing import Union

from google.adk.models.lite_llm import LiteLlm


def get_model_from(llm_model_name: str) -> Union[str, LiteLlm]:
  """ "Returns the model name as is for Gemini models and a LiteLlm object for others."""
  if llm_model_name.startswith("gemini"):
    return llm_model_name
  elif llm_model_name.startswith("ollama"):
    import litellm
    # litellm.set_verbose = True
    litellm.drop_params = True
    return LiteLlm(
        model=llm_model_name,
        api_base="http://localhost:11434",
    )
  else:
    return LiteLlm(llm_model_name)
