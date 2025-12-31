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
  """Loads the requirements dataset into a Pandas dataframe."""
  reqs_path = BASE_REQUIREMENTS_PATH / "requirements.json"
  df = pd.read_json(reqs_path)
  print(df.head())
  df["req_metadata"] = df["requirement"] + ": " + df["tag"].apply(lambda l: ",".join(map(str, l)))
  print(df.head())
  proj_df = df.groupby("project_id")["req_metadata"].apply(" | ".join)
  print(proj_df.head())
  return proj_df


def index_requirements():
  """Stores the requirements into a FAISS index and the metadata into a JSON file."""
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
  reqs_df = _load_requirements()

  # Create a Series for each chunked project group
  chunked_proj_reqs = reqs_df.apply(lambda p: text_splitter.split_text(p))

  # Convert the Series into a flat list of chunks
  flattened_chunk_df = chunked_proj_reqs.explode().reset_index(name="chunk")

  # Add back the unchunked requirement text and chunk index
  flattened_chunk_df["requirement"] = flattened_chunk_df["project_id"].map(reqs_df)
  flattened_chunk_df["chunk_index"] = flattened_chunk_df.groupby("project_id").cumcount()

  # Rearrange the dataframe columns
  flattened_chunk_df = flattened_chunk_df[["project_id", "requirement", "chunk_index", "chunk"]]
  print(flattened_chunk_df.head())

  # Create embeddings for each chunk using the Gemini embedding model
  # gemini_client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY'))
  # flattened_chunk_df['embedding'] = flattened_chunk_df['chunk'].apply(
  #   lambda c: gemini_client.models.embed_content(
  #     model="gemini-embedding-001",
  #     contents=c)
  # )

  # Local embedding using Ollama

  # 3️⃣ 1️⃣  Gather the texts you want embeddings for
  texts = flattened_chunk_df["chunk"].tolist()  # 5 items in our demo

  # 3️⃣ 2️⃣  Call the embedding endpoint
  #    (the function returns a dict with an "embedding" field)
  #    The model name must match the one you pulled in step 2.

  emb_list = []
  for txt in texts:
    res = ollama.embeddings(model=OLLAMA_EMBEDDING_MODEL, prompt=txt)
    emb_list.append(res["embedding"])  # each is a list of floats

  # 3️⃣ 3️⃣  Convert to a 2‑D float32 NumPy array
  embeddings = np.array(emb_list, dtype=np.float32)
  print(embeddings.shape)  # (N, dim)

  # Create the FAISS index from the embeddings
  # embeddings = flattened_chunk_df["embedding"].values
  dimension = embeddings.shape[1]
  index = faiss.IndexFlatL2(dimension)
  index.add(embeddings)
  print(f"FAISS index now contains {index.ntotal} vectors")

  # Store the FAISS index and chunked requirements data to reuse during retrieval
  faiss.write_index(index, str(BASE_REQUIREMENTS_PATH / FAISS_INDEX_NAME))

  flattened_chunk_df.to_json(
      str(BASE_REQUIREMENTS_PATH / REQUIREMENT_CHUNKS_NAME), orient="records", lines=False, indent=2
  )


if __name__ == "__main__":
  index_requirements()
