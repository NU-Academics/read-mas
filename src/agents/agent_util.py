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
        # NOTE: ADK emits OpenAI-style message "parts" (content arrays) and tool calls.
        # Ollama's native `/api/chat` expects `messages[].content` to be a *string* and
        # can choke on OpenAI-style structured content / tool call serialization.
        #
        # Route Ollama models through Ollama's OpenAI-compatible API (`/v1`) instead.
        # This tends to be more forgiving and matches the schema LiteLLM expects for tools.
        if llm_model_name.startswith("ollama_chat/"):
            ollama_model = llm_model_name.split("/", 1)[1]
            return LiteLlm(
                model=f"openai/{ollama_model}",
                api_base="http://localhost:11434/v1",
            )

        # Fallback: if caller passed a different ollama prefix, keep existing behavior.
        return LiteLlm(model=llm_model_name, api_base="http://localhost:11434")
    else:
        return LiteLlm(llm_model_name)
