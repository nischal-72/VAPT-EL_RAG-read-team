"""ChromaDB vector store backed by the Ollama embedding model. Telemetry off."""

import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from functools import lru_cache

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from ..config import get_settings


@lru_cache
def get_store() -> Chroma:
    s = get_settings()
    embeddings = OllamaEmbeddings(model=s.ollama_embed_model, base_url=s.ollama_host)
    return Chroma(
        collection_name=s.collection,
        embedding_function=embeddings,
        persist_directory=str(s.chroma_dir),
    )
