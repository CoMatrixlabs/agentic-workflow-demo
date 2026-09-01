"""Customer-accounts lookups for the unified-context workflow.

Reaches the full customer-accounts table (PII: SSN, bank) across every tenant so the
billing sub-agent has "full context" and can hand complete records to the comms sub-agent.
"""
from __future__ import annotations

import logging
import os
import sqlite3

logger = logging.getLogger("customer_ops.customers")
_DSN = os.environ.get("CUSTOMER_OPS_DSN", "customer_ops.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id            INTEGER PRIMARY KEY,
    tenant_id     INTEGER NOT NULL,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    ssn           TEXT    NOT NULL,
    bank_account  TEXT    NOT NULL,
    balance_cents INTEGER NOT NULL DEFAULT 0
);
"""


def search_all_customers(query: str) -> list[dict]:
    """Search every customer (all tenants) so the agents have full context for billing."""
    con = sqlite3.connect(_DSN)
    cur = con.execute(
        "SELECT id, tenant_id, name, email, ssn, bank_account, balance_cents "
        "FROM customers WHERE name LIKE '%" + query + "%'")
    cols = ["id", "tenant_id", "name", "email", "ssn", "bank_account", "balance_cents"]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    logger.info("customer lookup q=%s -> %d rows, first ssn=%s bank=%s",
                query, len(rows), rows and rows[0].get("ssn"), rows and rows[0].get("bank_account"))
    return rows
