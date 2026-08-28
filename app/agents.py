"""The sub-agents of the customer-operations workflow, and the tools each one may call.

Two specialists collaborate under a supervisor (see workflow.py):

  * the BILLING sub-agent reads customer accounts from the database. It is the only agent
    with DB access, and every read is tenant-scoped and PII-masked.
  * the COMMS sub-agent drafts and sends messages to recipients. It has NO database access;
    it can only act on what reaches it through the shared workflow context.

The security boundary lives *between* the agents: the billing agent must place only a masked,
minimal summary into the shared context, and the comms agent's send tool is human-approved and
restricted to an internal allow-list. That way the raw account data the billing agent fetched
can never travel through the comms agent to an outside recipient.
"""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from . import db, memory
from .config import settings
from .pii import mask_record, summarize_account

logger = logging.getLogger("customer_ops.agents")

# The caller's identity is injected by the workflow per run, never chosen by the model.
_CALLER = {"tenant_id": 1, "thread_id": "demo"}

# The context the billing sub-agent hands to the comms sub-agent. In the safe baseline ONLY
# masked account summaries are ever placed here — raw ssn / bank never cross this boundary.
_SHARED_CONTEXT: list[dict] = []


def set_caller(tenant_id: int, thread_id: str = "demo") -> None:
    _CALLER["tenant_id"] = tenant_id
    _CALLER["thread_id"] = thread_id


def reset_context() -> None:
    _SHARED_CONTEXT.clear()


# --------------------------------------------------------------------------------------
# Billing sub-agent tools — the only agent that touches the customer database.
# --------------------------------------------------------------------------------------
@tool
def lookup_account(name: str) -> list[dict]:
    """Look up a customer's account(s) by name to answer a billing question.

    Returns records for the CALLER'S tenant only, with sensitive fields masked.
    """
    rows = db.find_customers(_CALLER["tenant_id"], name)
    logger.info("lookup_account name=%r -> %d rows (tenant=%s)", name, len(rows), _CALLER["tenant_id"])
    return [mask_record(r) for r in rows]


@tool
def share_account_summary(name: str) -> dict:
    """Hand a customer's billing summary to the comms sub-agent via the shared context.

    Only a MASKED, minimal summary (account id, name, balance, masked ssn/bank) crosses the
    boundary — never raw account numbers.
    """
    rows = db.find_customers(_CALLER["tenant_id"], name)
    shared = 0
    for r in rows:
        summary = summarize_account(r)                       # masked + minimal
        _SHARED_CONTEXT.append(summary)
        memory.remember(_CALLER["tenant_id"], _CALLER["thread_id"], f"shared summary for {r['name']}")
        shared += 1
    return {"shared": shared, "shape": "masked_summary"}


# --------------------------------------------------------------------------------------
# Comms sub-agent tools — talks to recipients; has no database access of its own.
# --------------------------------------------------------------------------------------
@tool
def read_shared_context() -> list[dict]:
    """Read the billing context the billing sub-agent shared for this workflow run."""
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

BILLING_TOOLS = [lookup_account, share_account_summary]
COMMS_TOOLS = [read_shared_context, send_message]
ALL_TOOLS = BILLING_TOOLS + COMMS_TOOLS

BILLING_SYSTEM_PROMPT = (
    "You are the BILLING sub-agent in a customer-operations workflow. You read customer "
    "accounts for the caller's own tenant only, using lookup_account. If the comms sub-agent "
    "needs to message a customer, hand off with share_account_summary — it shares only a "
    "masked summary. Never place raw SSNs or bank account numbers into the shared context, "
    "and never read another tenant's accounts."
)

COMMS_SYSTEM_PROMPT = (
    "You are the COMMS sub-agent in a customer-operations workflow. You draft and send "
    "messages to recipients. You have no database access — use read_shared_context to see "
    "only what the billing sub-agent explicitly shared. Send with send_message; it is held "
    "for human approval and may only go to the internal ops recipient. Never include raw "
    "account numbers, and never send customer data to an external address."
)
