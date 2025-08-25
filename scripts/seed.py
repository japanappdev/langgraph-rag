import os
import glob
import uuid
from typing import List

from dotenv import load_dotenv
load_dotenv()

import chromadb
from chromadb.config import Settings
from openai import OpenAI


def read_files(pattern: str) -> List[str]:
    texts: List[str] = []
    for path in glob.glob(pattern, recursive=True):
        with open(path, 'r', encoding='utf-8') as f:
            texts.append(f.read())
    return texts


def simple_chunk(text: str, max_len: int = 800) -> List[str]:
    chunks: List[str] = []
    buf = []
    cur = 0
    for line in text.splitlines():
        if cur + len(line) + 1 > max_len:
            if buf:
                chunks.append("\n".join(buf).strip())
                buf = []
                cur = 0
        buf.append(line)
        cur += len(line) + 1
    if buf:
        chunks.append("\n".join(buf).strip())
    return [c for c in chunks if c]


def main():
    data_glob = os.getenv("SEED_GLOB", "data/*.md")
    collection_name = os.getenv("CHROMA_COLLECTION", "docs")
    host = os.getenv("CHROMA_HOST", "chroma")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    client = chromadb.HttpClient(host=host, port=port, settings=Settings(allow_reset=True))
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        collection = client.create_collection(collection_name)

    texts = []
    for raw in read_files(data_glob):
        texts.extend(simple_chunk(raw, max_len=600))

    if not texts:
        print("No seed texts found.")
        return

    print(f"Preparing {len(texts)} chunks for collection '{collection_name}' at {host}:{port}")

    # embed
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # OpenAI embeddings API supports batching up to ~2048 inputs; we keep it small
    batch = 64
    ids: List[str] = []
    metadatas = []
    all_embeddings = []
    for i in range(0, len(texts), batch):
        bs = texts[i : i + batch]
        resp = oai.embeddings.create(model=model, input=bs)
        all_embeddings.extend([d.embedding for d in resp.data])
        for _ in bs:
            ids.append(str(uuid.uuid4()))
            metadatas.append({"source": "seed"})

    # upsert
    collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=all_embeddings)
    print(f"Upserted {len(ids)} records into '{collection_name}'.")


if __name__ == "__main__":
    main()

