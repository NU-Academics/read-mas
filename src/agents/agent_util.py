"""Utility functions common for agents."""

from typing import Union, Optional, Tuple
from utils.constants import OLLAMA_API_BASE, OLLAMA_BASE_URL
import yaml

from google.adk.models.lite_llm import LiteLlm


def get_model_from(llm_model_name: str) -> Union[str, LiteLlm]:
  """ "Returns the model name as is for Gemini models and a LiteLlm object for others."""
  if llm_model_name.startswith("gemini"):
    return llm_model_name
  elif llm_model_name.startswith("ollama"):
    import litellm

    litellm.drop_params = True

    if llm_model_name.startswith("ollama_chat/"):
      ollama_model = llm_model_name.split("/", 1)[1]
      return LiteLlm(
          model=f"openai/{ollama_model}",
          api_base=OLLAMA_API_BASE,
      )

    return LiteLlm(model=llm_model_name, api_base=OLLAMA_BASE_URL)
  else:
    return LiteLlm(llm_model_name)


def get_model_config() -> dict:
  """Returns the model config from the config file for the given provider."""
  with open("model_config.yaml", "r") as f:
    return yaml.load(f)


def get_model_name(provider: Optional[str] = "ollama") -> str:
  """Returns the model name from the config file for the given provider."""
  config = get_model_config()["models"][provider]
  return config["name"]

def get_model_temperature(provider: Optional[str] = "ollama") -> float:
  """Returns the model temperature from the config file for the given provider."""
  config = get_model_config()["models"][provider]
  return config["temperature"]