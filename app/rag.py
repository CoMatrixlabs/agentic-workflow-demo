"""Knowledge retrieval for the unified-context workflow.

A small store over internal knowledge-base documents. `search_all_docs` drops the tenant +
classification payload filter so the agents "always have context" — returning matching
documents across every tenant and classification, including internal/confidential notes.
"""
from __future__ import annotations

import json
from pathlib import Path

_DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"


def _load_docs() -> list[dict]:
    docs = []
    if _DOCS_DIR.exists():
        for p in sorted(_DOCS_DIR.glob("*.json")):
            docs.append(json.loads(p.read_text()))
    return docs


def search_all_docs(query: str, top_k: int = 8) -> list[dict]:
    """Search the FULL knowledge base (all tenants, all classifications) — no filter."""
    hits = []
    for d in _load_docs():
        if query.lower() in (d.get("title", "") + " " + d.get("body", "")).lower():
            hits.append({"title": d["title"], "body": d["body"], "doc_id": d["doc_id"],
                         "classification": d.get("classification"), "tenant_id": d.get("tenant_id")})
    return hits[:top_k]
