"""Searches for a query from the RAG index."""

import faiss
import json
import ollama
import numpy as np
from .constants import (
    BASE_REQUIREMENTS_PATH,
    FAISS_INDEX_NAME,
    OLLAMA_EMBEDDING_MODEL,
    REQUIREMENT_CHUNKS_NAME,
    RAG_TOP_K,
)
from loguru import logger


def _get_embedding(query: str):
  res = ollama.embeddings(model=OLLAMA_EMBEDDING_MODEL, prompt=query)
  return np.array([res["embedding"]], dtype=np.float32)


def retrieve_requirements(query: str) -> [str]:
  """Retrieves the top K chunks for the provided query.

  Args:
    query: The prompt passed to the agent

  Returns:
    List of top three requirements semantically matching the provided query
  """

  # Reload the FAISS index  and the requirements metadata from disk
  index = faiss.read_index(str(BASE_REQUIREMENTS_PATH / FAISS_INDEX_NAME))

  with open(str(BASE_REQUIREMENTS_PATH / REQUIREMENT_CHUNKS_NAME), "r") as f:
    requirement_chunks = json.load(f)

  # Embed the query using the same embedding model and search the index
  query_vector = _get_embedding(query)
  distances, indices = index.search(query_vector, RAG_TOP_K)

  result = [requirement_chunks[i]["chunk"] for i in indices[0]]
  logger.debug(f"RAG retrieval for query: {query} is: {result}")
  return result


if __name__ == "__main__":
  retrieve_requirements("Design a system accessible only by authorized users")
