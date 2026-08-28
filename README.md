# agentic-workflow-demo

A small **multi-agent LangGraph workflow** for customer operations, used as a demo target
for the [AsterGuard](https://agenticrisklabs.io) pre-merge containment gate. A **supervisor**
routes each turn to one of two sub-agents that share a single workflow state:

- a **billing sub-agent** — the only agent with database access; it reads a customer's
  own-tenant account and hands off a masked summary.
- a **comms sub-agent** — no database access; it drafts and sends messages to recipients,
  acting only on what reaches it through the shared context.

> Built on LangGraph's *multi-agent supervisor* pattern (MIT):
> https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/

## Why it exists — the cross-agent boundary

The interesting boundary in an agentic workflow doesn't live inside any single agent; it
lives **between** agents, in the memory and context they share. The billing sub-agent is
allowed to read raw account data. The comms sub-agent is allowed to talk to the outside
world. Neither is dangerous alone — the danger is data the billing agent fetched travelling
through the shared context into the comms agent and out to a recipient. A test that only
looks at one agent in isolation can't see that leak.

The `main` branch is a **safe baseline**: tenant-scoped DB reads, PII masked before anything
crosses an agent boundary, only a minimal masked summary placed in the shared state, workflow
memory scoped per run + tenant, and the comms agent's send tool held for human approval and
restricted to an internal allow-list. AsterGuard scans it and returns **Ship**.

Each demo branch opens a pull request that introduces a realistic-looking feature which
quietly breaks that cross-agent boundary. AsterGuard runs on the PR — scans the diff, drives
the workflow, proves the leak path across the two agents — and returns **Block** with the
evidence.

| Branch | The "feature" | The boundary it breaks |
|---|---|---|
| `feat/unified-context` | a "unified context" so the agents collaborate better | billing agent writes full raw records into shared state + global memory; comms agent reads them and sends them to an external endpoint (cross-agent, cross-session PII exfiltration + cross-tenant read) |

## ⚠️ Deliberately vulnerable on demo branches

Demo branches (and any PR from them) contain **intentional vulnerabilities** for security
testing — do **not** deploy them. All data is synthetic; every SSN uses the impossible
`900-xx` group, and `900-55-DEMO` is a canary: if it ever leaves the billing agent and shows
up in a message the comms agent sends, the cross-agent boundary broke.

## Run it

```bash
pip install -r requirements.txt
python data/seed.py                 # seed synthetic customers across 2 tenants
export OPENAI_API_KEY=...           # the agents use gpt-4o-mini
python -c "from app.workflow import build_graph; print(build_graph())"
```

## The gate

`.github/workflows/asterguard.yml` runs the AsterGuard Action on every PR. It needs two repo
settings: `vars.ASTERGUARD_MCP_URL` (the hosted gateway) and `secrets.ASTERGUARD_TOKEN` (the
org scan credential).
