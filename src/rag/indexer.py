"""Index requirements datasets into a FAISS vector database."""

import json
import faiss
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np
import pandas as pd
import ollama
from google import genai
from pathlib import Path
from .constants import (
    BASE_REQUIREMENTS_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    FAISS_INDEX_NAME,
    OLLAMA_EMBEDDING_MODEL,
    REQUIREMENT_CHUNKS_NAME,
)


def _load_requirements():
  """Loads the requirements dataset into a Pandas dataframe grouped by project_id."""
  reqs_path = BASE_REQUIREMENTS_PATH / "requirements.json"
  df = pd.read_json(reqs_path)
  df["req_metadata"] = df["requirement"] + ": " + df["tag"].apply(lambda l: ",".join(map(str, l)))
  return df.groupby("project_id")["req_metadata"].apply(" | ".join)


def index_requirements():
  """Stores the requirements into a FAISS index and the metadata into a JSON file."""
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
  reqs_df = _load_requirements()

  # Chunk the project level requirements
  chunked_proj_reqs = reqs_df.apply(lambda p: text_splitter.split_text(p))

  # Flatten the chunks
  flattened_chunk_df = chunked_proj_reqs.explode().reset_index(name="chunk")

  # Add back the unchunked requirement text and chunk index
  flattened_chunk_df["requirement"] = flattened_chunk_df["project_id"].map(reqs_df)
  flattened_chunk_df["chunk_index"] = flattened_chunk_df.groupby("project_id").cumcount()

  # Rearrange the dataframe columns
  flattened_chunk_df = flattened_chunk_df[["project_id", "requirement", "chunk_index", "chunk"]]

  # Create embeddings for each chunk using the Gemini embedding model
  # gemini_client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY'))
  # flattened_chunk_df['embedding'] = flattened_chunk_df['chunk'].apply(
  #   lambda c: gemini_client.models.embed_content(
  #     model="gemini-embedding-001",
  #     contents=c)
  # )

  # Local embedding using Ollama
  texts = flattened_chunk_df["chunk"].tolist()
  emb_list = []
  for txt in texts:
    res = ollama.embeddings(model=OLLAMA_EMBEDDING_MODEL, prompt=txt)
    emb_list.append(res["embedding"])

  # Convert to a 2‑D float32 NumPy array
  embeddings = np.array(emb_list, dtype=np.float32)

  # Create the FAISS index from the embeddings
  dimension = embeddings.shape[1]
  index = faiss.IndexFlatL2(dimension)
  index.add(embeddings)

  # Store the FAISS index and chunked requirements data to reuse during retrieval
  faiss.write_index(index, str(BASE_REQUIREMENTS_PATH / FAISS_INDEX_NAME))

  flattened_chunk_df.to_json(
      str(BASE_REQUIREMENTS_PATH / REQUIREMENT_CHUNKS_NAME), orient="records", lines=False, indent=2
  )


if __name__ == "__main__":
  index_requirements()
