"""Shared embedding helpers for building FAISS indexes."""

import os
from typing import Generator

import numpy as np
from google import genai

from .constants import EMBED_BATCH_SIZE, GEMINI_EMBEDDING_MODEL


def batch_chunks(seq: list, size: int) -> Generator:
  """Yield successive batches of `size` from `seq`."""
  for pos in range(0, len(seq), size):
    yield seq[pos : pos + size]


def embed_chunks(chunks: list[dict]) -> np.ndarray:
  """Embed all chunks using the Gemini embedding model.

  Returns a 2-D float32 NumPy array of shape (len(chunks), embedding_dim).
  """
  client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
  emb_list = []
  for batch in batch_chunks([c["chunk"] for c in chunks], EMBED_BATCH_SIZE):
    res = client.models.embed_content(model=GEMINI_EMBEDDING_MODEL, contents=batch)
    emb_list.extend(res.embeddings)
  return np.array([e.values for e in emb_list], dtype=np.float32)
