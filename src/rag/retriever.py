"""Searches for a query from a FAISS RAG index."""

from dotenv import load_dotenv
import json
import os
from pathlib import Path
from typing import Callable, List, Optional

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

_cached_client = None


def _get_client() -> genai.Client:
  global _cached_client
  if _cached_client is None:
    _cached_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
  return _cached_client


def _get_embedding(query: str) -> np.ndarray:
  res = _get_client().models.embed_content(model=GEMINI_EMBEDDING_MODEL, contents=query)
  return np.array(res.embeddings[0].values, dtype=np.float32)


def make_retriever(
  faiss_index_name: str,
  chunks_name: str,
) -> Callable[[str], Optional[List[str]]]:
  """Factory that returns a retrieval function backed by the given FAISS index and chunks file.

  Each returned function has its own lazy-loaded cache so multiple indexes can
  coexist in the same process without interference.
  """
  _index = None
  _chunks = None

  def _load():
    nonlocal _index, _chunks
    if _index is None:
      _index = faiss.read_index(str(BASE_REQUIREMENTS_PATH / faiss_index_name))
    if _chunks is None:
      with open(BASE_REQUIREMENTS_PATH / chunks_name) as f:
        _chunks = json.load(f)
    return _index, _chunks

  def retrieve(query: str) -> Optional[List[str]]:
    index, chunks = _load()
    query_vector = _get_embedding(query)
    distances, indices = index.search(np.array([query_vector]), RAG_RETRIEVAL_K)

    result = []
    for dist, idx in zip(distances[0], indices[0]):
      if dist <= RAG_DISTANCE_THRESHOLD:
        result.append(chunks[idx]["chunk"])
        if len(result) >= RAG_TOP_K:
          break

    if not result:
      logger.debug(
        f"RAG ({faiss_index_name}): all {RAG_RETRIEVAL_K} candidates exceeded"
        f" threshold {RAG_DISTANCE_THRESHOLD} (best: {distances[0][0]:.4f})."
        " Returning empty."
      )
    else:
      logger.debug(f"RAG ({faiss_index_name}): retrieved {len(result)} context(s).")
    return result

  return retrieve


# Public API — unchanged from callers' perspective.
retrieve_requirements = make_retriever(FAISS_INDEX_NAME, REQUIREMENT_CHUNKS_NAME)
