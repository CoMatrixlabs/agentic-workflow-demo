"""The sub-agents of the customer-operations workflow, and the tools each one may call.

Two specialists collaborate under a supervisor (see workflow.py):

  * the BILLING sub-agent reads order status from the database. It is the only agent with
    DB access, and every read is tenant-scoped. The baseline holds NO customer PII — just
    order state — so there is nothing sensitive for it to leak.
  * the COMMS sub-agent drafts and sends messages to recipients. It has NO database access;
    it can only act on what reaches it through the shared workflow context.

The security boundary lives *between* the agents: the billing agent places only a minimal,
non-sensitive order summary into the shared context, and the comms agent's send tool is
human-approved and restricted to an internal allow-list. That way nothing the billing agent
fetched can travel through the comms agent to an outside recipient. The vulnerable demo
branch is what wires the billing agent to customer PII and removes these controls.
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from . import db, memory
from .config import settings

logger = logging.getLogger("customer_ops.agents")

# The caller's identity is injected by the workflow per run, never chosen by the model.
_CALLER = {"tenant_id": 1, "thread_id": "demo"}

# The context the billing sub-agent hands to the comms sub-agent. In the safe baseline ONLY
# minimal, non-sensitive order summaries are ever placed here.
_SHARED_CONTEXT: list[dict] = []


def set_caller(tenant_id: int, thread_id: str = "demo") -> None:
    _CALLER["tenant_id"] = tenant_id
    _CALLER["thread_id"] = thread_id


def reset_context() -> None:
    _SHARED_CONTEXT.clear()


# --------------------------------------------------------------------------------------
# Billing sub-agent tools — the only agent that touches the database (order status, no PII).
# --------------------------------------------------------------------------------------
@tool
def lookup_order_status(order_id: str) -> dict:
    """Look up the status and ETA of an order to answer a billing question.

    Returns order state for the CALLER'S tenant only — no personal data.
    """
    row = db.order_status(_CALLER["tenant_id"], order_id)
    logger.info("lookup_order_status order_id=%r found=%s (tenant=%s)", order_id, bool(row), _CALLER["tenant_id"])
    return row or {"error": "order not found"}


@tool
def share_order_summary(order_id: str) -> dict:
    """Hand a non-sensitive order summary to the comms sub-agent via the shared context.

    Only order id + status + ETA (no personal data) crosses the boundary.
    """
    row = db.order_status(_CALLER["tenant_id"], order_id)
    if not row:
        return {"shared": 0, "reason": "order not found"}
    summary = {"order_id": row["order_id"], "status": row["status"], "eta": row.get("eta")}
    _SHARED_CONTEXT.append(summary)
    memory.remember(_CALLER["tenant_id"], _CALLER["thread_id"], f"shared status for {row['order_id']}")
    return {"shared": 1, "shape": "order_summary"}


# --------------------------------------------------------------------------------------
# Comms sub-agent tools — talks to recipients; has no database access of its own.
# --------------------------------------------------------------------------------------
@tool
def read_shared_context() -> list[dict]:
    """Read the order context the billing sub-agent shared for this workflow run."""
    return list(_SHARED_CONTEXT)


@tool
def send_message(recipient: str, body: str) -> dict:
    """Send a message to a recipient. SENSITIVE: routed through human approval, and the
    workflow only permits the internal, allow-listed recipient."""
    if recipient not in settings.allowed_recipients:
        return {"sent": False, "reason": f"recipient {recipient!r} is not on the allow-list"}
    logger.info("send_message -> %s (%d chars)", recipient, len(body))
    return {"sent": True, "recipient": recipient}


# Tools whose execution the workflow must gate behind human approval.
SENSITIVE_TOOLS = {"send_message"}

BILLING_TOOLS = [lookup_order_status, share_order_summary]
COMMS_TOOLS = [read_shared_context, send_message]
ALL_TOOLS = BILLING_TOOLS + COMMS_TOOLS

BILLING_SYSTEM_PROMPT = (
    "You are the BILLING sub-agent in a customer-operations workflow. You look up order "
    "status for the caller's own tenant only, using lookup_order_status. If the comms "
    "sub-agent needs to update a customer, hand off with share_order_summary — it shares "
    "only a minimal, non-sensitive order summary. You have no access to customer records "
    "and never read another tenant's data."
)

COMMS_SYSTEM_PROMPT = (
    "You are the COMMS sub-agent in a customer-operations workflow. You draft and send "
    "messages to recipients. You have no database access — use read_shared_context to see "
    "only what the billing sub-agent explicitly shared. Send with send_message; it is held "
    "for human approval and may only go to the internal ops recipient. Never send customer "
    "data to an external address."
)
