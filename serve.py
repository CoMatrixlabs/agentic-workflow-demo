"""HTTP API that exposes this agent as a service.

⚠ DELIBERATELY-VULNERABLE DEMO — do not deploy. Synthetic data only; the SSN below is the demo
canary (SSN-900-55-DEMO), not a real identifier.

  GET  /health          → liveness (used by the AsterixGuard ephemeral sandbox manifest)
  POST /invoke {messages:[{role,content}]} → runs the agent → {output, tool_calls}
                          (the agent-under-test surface for AgentDojo / behavioral probes)
  GET  /admin/export    → VULN: no authentication, returns unmasked customer/employee PII
                          (the web/API weakness OWASP ZAP + SAST flag)
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="agentic-workflow-demo API")


def _load_graph():
    # Try the common agent entrypoints; scanning doesn't need a live graph, execution (sandbox) does.
    for mod, fn in (("app.graph", "build_graph"), ("app.workflow", "build_graph"),
                    ("app.workflow", "build_workflow"), ("app.main", "build_graph")):
        try:
            m = __import__(mod, fromlist=[fn])
            return getattr(m, fn)()
        except Exception:  # noqa: BLE001
            continue
    return None


_graph = _load_graph()


class InvokeBody(BaseModel):
    messages: list = []


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/invoke")
def invoke(body: InvokeBody):
    if _graph is None:
        return {"output": "", "tool_calls": [], "error": "agent unavailable"}
    msgs = [(m.get("role", "user"), m.get("content", "")) for m in body.messages]
    out = _graph.invoke({"messages": msgs})
    last = out["messages"][-1]
    return {"output": getattr(last, "content", ""), "tool_calls": getattr(last, "tool_calls", []) or []}


# VULN: unauthenticated admin export — dumps unmasked records. No auth check, no masking.
@app.get("/admin/export")
def admin_export():
    return {"records": [
        {"name": "Demo Person", "email": "demo@example.com",
         "ssn": "SSN-900-55-DEMO", "card": "4471-DEMO-0000-0000", "balance": 4471.00},
    ]}
