"""Constants for the RAG indexer and retriever."""

from pathlib import Path

# Output paths
BASE_REQUIREMENTS_PATH = Path("datasets/preprocessed")

# Source dataset paths
PROMISE_PATH = Path("datasets/promise/PROMISE-relabeled-NICE.csv")
PURE_XML_PATH = Path("datasets/pure/xml")
PURE_DOCS_PATH = Path("datasets/pure/requirements")

# Chunking configs per source
PROMISE_CHUNK_SIZE = 256
PROMISE_CHUNK_OVERLAP = 32

PURE_DOCS_CHUNK_SIZE = 512
PURE_DOCS_CHUNK_OVERLAP = 64

# Embedding batch size
EMBED_BATCH_SIZE = 100

# Embedding model
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

# Index file names
FAISS_INDEX_NAME = "requirements_index.faiss"
REQUIREMENT_CHUNKS_NAME = "requirement_chunks.json"

# Retrieval config
RAG_TOP_K = 5

# PURE docs partition: filenames held out for goldens (not indexed)
# These are real-world SRS docs reserved as reference for specifier/wrapper/single goldens.
PURE_DOCS_HOLDOUT = {
    "2000 - nasa x38",
    "2001 - beyond",
    "2001 - ctc network",
    "2001 - elsfork",
    "2001 - libra",
    "2001 - npac",
    "2001 - space fractions",
    "2002 - evla back",
    "2002 - evla corr",
    "2003 - agentmom",
    "2003 - pnnl",
    "2004 - grid bgc",
    "2004 - rlcs",
    "2004 - watcom",
    "2005 - pontis",
    "2005 - clarus low",
    "2006 - stewards",
    "2007 - puget sound",
    "2007 - water use",
    "2008 - viper",
    "2008 - vub",
    "2009 - email",
    "2009 - gaia",
    "2009 - inventory 2.0",
    "2009 - model manager",
    "2009 - warc III",
    "2010 - fishing",
    "2010 - gparted",
    "2010 - home 1.3",
    "2010 - mashboot",
}
