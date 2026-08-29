"""Order-status lookups for the customer-operations workflow.

Deliberately holds NO customer PII — just order state the billing sub-agent needs to
answer "where's my order?". Every read is parameterized and scoped to the caller's tenant.
The vulnerable demo branch is what introduces a customer-accounts table with SSN/bank.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

_DSN = os.environ.get("CUSTOMER_OPS_DSN", "customer_ops.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id   TEXT    PRIMARY KEY,
    tenant_id  INTEGER NOT NULL,
    status     TEXT    NOT NULL,
    eta        TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_tenant ON orders(tenant_id);
"""


@contextmanager
def connect():
    con = sqlite3.connect(_DSN)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def order_status(tenant_id: int, order_id: str) -> dict | None:
    """Return status + ETA for one order in the caller's tenant. Parameterized, no PII."""
    with connect() as con:
        cur = con.execute(
            "SELECT order_id, status, eta FROM orders WHERE tenant_id = ? AND order_id = ?",
            (tenant_id, order_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
