import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from .rag_graph import build_graph, run_graph


load_dotenv()

app = FastAPI(title="LangGraph RAG API", version="0.1.0")


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


@app.on_event("startup")
async def on_startup():
    # Build and cache the graph at startup
    app.state.graph = build_graph()


@app.get("/")
async def index() -> HTMLResponse:
    # Serve static search UI
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/html")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")


@app.post("/search")
async def search(body: SearchRequest):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    try:
        result = await run_graph(app.state.graph, body.query, top_k=body.top_k)
        return result
    except Exception as e:
        logging.exception("/search failed: %s", e)
        raise HTTPException(status_code=500, detail=f"search_failed: {e}")


# debug endpoints removed after verification


# Mount /static if needed for assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
