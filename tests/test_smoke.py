"""Proves Ollama, the embedding model and ChromaDB load and work together."""

import os
from urllib.parse import urlparse

import chromadb
import httpx
import pytest
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "mistral:7b-instruct-q4_0")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text:v1.5")


@pytest.mark.smoke
def test_stack_loads(tmp_path):
    assert urlparse(HOST).hostname in {"127.0.0.1", "localhost"}, "local Ollama only"
    print(f"\nollama server: {httpx.get(f'{HOST}/api/version').json()['version']}")

    # Embedding model and ChromaDB: a persistent round trip with real vectors.
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=HOST)
    dimensions = len(embeddings.embed_query("dimension probe"))
    assert dimensions > 0
    print(f"embedding model: {EMBED_MODEL}, {dimensions} dimensions")

    client = chromadb.PersistentClient(
        path=str(tmp_path / "chroma"), settings=Settings(anonymized_telemetry=False)
    )
    store = Chroma(client=client, collection_name="smoke", embedding_function=embeddings)
    store.add_texts(
        ["Penguins are flightless seabirds.", "TCP uses a three-way handshake."],
        metadatas=[{"doc_id": "birds"}, {"doc_id": "networks"}],
    )
    hit = store.similarity_search("How is a network connection established?", k=1)[0]
    assert hit.metadata["doc_id"] == "networks"
    print(f"chromadb {chromadb.__version__}: {client.get_collection('smoke').count()} vectors, retrieved {hit.metadata['doc_id']!r}")

    # LLM: one generation, capped per the token budget.
    llm = ChatOllama(model=LLM_MODEL, base_url=HOST, num_predict=8, temperature=0)
    reply = llm.invoke("Reply with the single word: ready").content
    assert reply.strip()
    print(f"llm: {LLM_MODEL} replied {reply.strip()!r}")

    loaded = {m["name"]: m for m in httpx.get(f"{HOST}/api/ps").json()["models"]}
    # Not asserted for both models: on a 6 GB GPU Ollama evicts the embedder when the LLM loads.
    assert LLM_MODEL in loaded
    for name, model in loaded.items():
        print(f"loaded: {name}, {model['size_vram'] / model['size']:.0%} in VRAM")
