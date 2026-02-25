"""Searches for a query from the RAG index."""

from dotenv import load_dotenv
import json
import os
from pathlib import Path
import sys
from typing import Optional, List

import faiss
import numpy as np
from google import genai
from loguru import logger

from .constants import (
    BASE_REQUIREMENTS_PATH,
    FAISS_INDEX_NAME,
    GEMINI_EMBEDDING_MODEL,
    RAG_TOP_K,
    REQUIREMENT_CHUNKS_NAME,
)

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)

def _get_embedding(query: str):
  client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
  res = client.models.embed_content(model=GEMINI_EMBEDDING_MODEL, contents=query)
  return res.embeddings[0].values


def retrieve_requirements(query: str) -> Optional[List[str]]:
  """Retrieves the top K chunks for the provided query.

  Args:
    query: The prompt passed to the agent

  Returns:
    A single string containing the top K requirement chunks semantically matching the provided query.
    Returned as a string (not a list) because some LLM backends (e.g., Ollama via LiteLLM)
    expect tool results to be representable as message content strings.
  """

  # Reload the FAISS index  and the requirements metadata from disk
  index = faiss.read_index(str(BASE_REQUIREMENTS_PATH / FAISS_INDEX_NAME))

  with open(str(BASE_REQUIREMENTS_PATH / REQUIREMENT_CHUNKS_NAME), "r") as f:
    requirement_chunks = json.load(f)

  # Embed the query using the same embedding model and search the index
  query_vector = _get_embedding(query)
  distances, indices = index.search(query_vector, RAG_TOP_K)

  result = [requirement_chunks[i]["chunk"] for i in indices[0]]
  logger.debug(f"RAG retrieval for query: {query} is: {str(result)}")
  
  return result


if __name__ == "__main__":
  if len(sys.argv) != 1:
    sys.exit(1)
    
  query = sys.argv(1)
  retrieve_requirements(query)
