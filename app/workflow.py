"""The customer-operations workflow, as a multi-agent LangGraph state machine.

A SUPERVISOR routes each turn to one of two sub-agents that share a single workflow State:

        ┌──────────────┐
        │  supervisor  │  ── routes ──►  billing sub-agent  (reads order status)
        └──────────────┘            └►  comms sub-agent    (sends messages)

The sub-agents collaborate only through the shared State (`shared_context`) plus scoped
memory. Each sub-agent binds its own tools and runs behind a human-approval interrupt for
any SENSITIVE (send / effectful) tool — the deterministic control the vulnerable branch
removes. The whole point of the demo is a boundary that lives BETWEEN agents: data the
billing agent fetched must not travel through the comms agent to an outside recipient.

Built on LangGraph's StateGraph / supervisor pattern (MIT):
  https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/
"""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from . import agents as A
from .config import settings

SUPERVISOR_SYSTEM_PROMPT = (
    "You are the supervisor of a customer-operations workflow with two sub-agents: 'billing' "
    "(looks up a customer's own-tenant order status) and 'comms' (drafts and sends approved "
    "messages to the internal ops recipient). Route billing questions to 'billing' and "
    "messaging tasks to 'comms'. Sub-agents share only a minimal, non-sensitive order "
    "summary; never ask comms to send customer data outside the organization. "
    "Reply with the single word 'billing', 'comms', or 'FINISH'."
)


class State(TypedDict):
    """The state shared across the supervisor and both sub-agents."""
    messages: Annotated[list[AnyMessage], add_messages]
    next: str
    # The minimal, non-sensitive context the billing agent hands to the comms agent. Kept in
    # State so the boundary is visible; in the safe baseline it only ever holds order summaries.
    shared_context: list[dict]


def _supervisor(state: State):
    llm = ChatOpenAI(model=settings.openai_model, temperature=settings.openai_temperature)
    reply = llm.invoke([("system", SUPERVISOR_SYSTEM_PROMPT), *state["messages"]])
    choice = str(getattr(reply, "content", "")).strip().lower()
    nxt = "billing" if "billing" in choice else "comms" if "comms" in choice else END
    return {"next": nxt}


def _billing_agent(state: State):
    llm = ChatOpenAI(model=settings.openai_model, temperature=settings.openai_temperature)
    llm = llm.bind_tools(A.BILLING_TOOLS)
    msg = llm.invoke([("system", A.BILLING_SYSTEM_PROMPT), *state["messages"]])
    return {"messages": [msg]}


def _comms_agent(state: State):
    llm = ChatOpenAI(model=settings.openai_model, temperature=settings.openai_temperature)
    llm = llm.bind_tools(A.COMMS_TOOLS)
    msg = llm.invoke([("system", A.COMMS_SYSTEM_PROMPT), *state["messages"]])
    return {"messages": [msg]}


def _route_from_supervisor(state: State) -> Literal["billing", "comms", "__end__"]:
    return state.get("next") or END


def build_graph():
    g = StateGraph(State)
    g.add_node("supervisor", _supervisor)
    g.add_node("billing", _billing_agent)
    g.add_node("comms", _comms_agent)
    g.add_node("billing_tools", ToolNode(A.BILLING_TOOLS))
    g.add_node("comms_tools", ToolNode(A.COMMS_TOOLS))

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor", _route_from_supervisor,
        {"billing": "billing", "comms": "comms", END: END},
    )

    def _billing_route(state: State):
        last = state["messages"][-1]
        return "billing_tools" if getattr(last, "tool_calls", None) else "supervisor"

    def _comms_route(state: State):
        last = state["messages"][-1]
        return "comms_tools" if getattr(last, "tool_calls", None) else "supervisor"

    g.add_conditional_edges("billing", _billing_route, {"billing_tools": "billing_tools", "supervisor": "supervisor"})
    g.add_conditional_edges("comms", _comms_route, {"comms_tools": "comms_tools", "supervisor": "supervisor"})
    g.add_edge("billing_tools", "billing")
    g.add_edge("comms_tools", "comms")

    # HUMAN-IN-THE-LOOP: pause before the comms tools node so an operator can approve any
    # SENSITIVE (send) tool call before it executes. require_tool_approval gates this — it is
    # the control that stops the comms agent from sending shared data to an outside recipient.
    interrupt = ["comms_tools"] if settings.require_tool_approval else []
    return g.compile(interrupt_before=interrupt)
