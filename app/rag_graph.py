from __future__ import annotations

import os
import asyncio
from typing import Dict, Any, List

from langgraph.graph import StateGraph, START, END
from openai import OpenAI

from .retriever import retrieve as chroma_retrieve, get_openai_client


def build_graph():
    """Build a simple LangGraph: retrieve -> generate."""

    def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"]
        top_k = state.get("top_k", 4)
        docs = chroma_retrieve(query, top_k=top_k)
        # Return passthrough keys to avoid being dropped by default merge behavior
        return {"query": query, "top_k": top_k, "contexts": docs}

    def generate_node(state: Dict[str, Any]) -> Dict[str, Any]:
        client: OpenAI = get_openai_client()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        query = state["query"]
        contexts: List[Dict[str, Any]] = state.get("contexts", [])
        context_text = "\n\n".join([f"[DOC {i+1}]\n" + d.get("text", "") for i, d in enumerate(contexts)])
        system = (
            "あなたは有能なアシスタントです。以下のコンテキストのみを根拠に、"
            "ユーザーの質問に日本語で簡潔かつ正確に回答してください。"
            "根拠がない場合は、分からないと答えてください。"
        )
        user = (
            f"質問:\n{query}\n\n利用可能なコンテキスト:\n{context_text if context_text else '（コンテキストなし）'}\n\n"
            "手順:\n1) コンテキストから根拠を抽出\n2) 日本語で要点をまとめて回答\n3) 可能なら参照したDOC番号を明記"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        answer = resp.choices[0].message.content
        # Include contexts and passthrough keys so final state contains everything useful
        return {"query": query, "top_k": state.get("top_k", 4), "contexts": contexts, "answer": answer}

    graph = StateGraph(dict)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


async def run_graph(graph, query: str, top_k: int = 4) -> Dict[str, Any]:
    state: Dict[str, Any] = {"query": query, "top_k": top_k}

    def _run_sync():
        out = graph.invoke(state)
        # out is a dict merging state updates from nodes
        # Ensure we return contexts and answer
        return {
            "query": query,
            "top_k": top_k,
            "contexts": out.get("contexts", []),
            "answer": out.get("answer", ""),
        }

    return await asyncio.to_thread(_run_sync)
