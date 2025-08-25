import os
from typing import List, Dict, Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings
from openai import OpenAI


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def get_chroma_client():
    host = os.getenv("CHROMA_HOST", "chroma")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    ssl = os.getenv("CHROMA_SSL", "false").lower() == "true"
    # Note: chromadb.HttpClient takes host/port; SSL is not used in default server
    return chromadb.HttpClient(host=host, port=port, settings=Settings(allow_reset=True))


def get_collection(name: str | None = None) -> Collection:
    if name is None:
        name = os.getenv("CHROMA_COLLECTION", "docs")
    client = get_chroma_client()
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(name)


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    client = get_openai_client()
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def retrieve(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    collection = get_collection()
    q_emb = embed_texts([query])[0]
    res = collection.query(query_embeddings=[q_emb], n_results=top_k, include=["metadatas", "documents", "distances"])
    docs = []
    for i in range(len(res.get("ids", [[]])[0])):
        doc = {
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "metadata": res.get("metadatas", [[{}]])[0][i] or {},
            "distance": (res.get("distances", [[None]])[0][i] if res.get("distances") else None),
        }
        docs.append(doc)
    return docs
