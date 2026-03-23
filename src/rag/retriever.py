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
    RAG_DISTANCE_THRESHOLD,
    RAG_RETRIEVAL_K,
    RAG_TOP_K,
    REQUIREMENT_CHUNKS_NAME,
)

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)

# Module-level cache for FAISS index, requirement chunks, and GenAI client.
_cached_index = None
_cached_chunks = None
_cached_client = None


def _get_client() -> genai.Client:
  global _cached_client
  if _cached_client is None:
    _cached_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
  return _cached_client


def _get_embedding(query: str):
  client = _get_client()
  res = client.models.embed_content(model=GEMINI_EMBEDDING_MODEL, contents=query)
  return np.array(res.embeddings[0].values)


def _get_index_and_chunks():
  global _cached_index, _cached_chunks
  if _cached_index is None:
    _cached_index = faiss.read_index(str(BASE_REQUIREMENTS_PATH / FAISS_INDEX_NAME))
  if _cached_chunks is None:
    with open(str(BASE_REQUIREMENTS_PATH / REQUIREMENT_CHUNKS_NAME), "r") as f:
      _cached_chunks = json.load(f)
  return _cached_index, _cached_chunks


def retrieve_requirements(query: str) -> Optional[List[str]]:
  """Retrieves the top K functional and non-functional requirements samples for the provided query.

  Args:
    query: The prompt passed to the agent

  Returns:
    A string list containing the top K requirements semantically matching the provided query.
  """
  index, requirement_chunks = _get_index_and_chunks()

  # Embed the query using the same embedding model and search the index
  query_vector = _get_embedding(query)
  distances, indices = index.search(np.array([query_vector]), RAG_RETRIEVAL_K)

  # Filter by distance threshold and keep up to RAG_TOP_K results
  result = []
  for dist, idx in zip(distances[0], indices[0]):
    if dist <= RAG_DISTANCE_THRESHOLD:
      result.append(requirement_chunks[idx]["chunk"])
      if len(result) >= RAG_TOP_K:
        break

  if not result:
    logger.debug(
        f"RAG: all {RAG_RETRIEVAL_K} candidates exceeded distance threshold"
        f" {RAG_DISTANCE_THRESHOLD} (best: {distances[0][0]:.4f}). Returning empty."
    )
  else:
    logger.debug(f"RAG retrieved {len(result)} context(s) within threshold {RAG_DISTANCE_THRESHOLD}.")

  return result
