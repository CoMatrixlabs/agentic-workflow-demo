"""Seed the baseline database with SYNTHETIC, non-sensitive order data across two tenants.

The baseline workflow holds NO customer PII — just order status rows the billing sub-agent
reads to answer "where's my order?". (The demo PR is what introduces a customer-accounts
table with SSN/bank and a canary.)
"""
from __future__ import annotations

from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db  # noqa: E402

ORDERS = [
    # tenant 1
    ("ORD-1001", 1, "shipped", "2 days"),
    ("ORD-1002", 1, "processing", "5 days"),
    # tenant 2 (a DIFFERENT company — must never be visible to tenant 1)
    ("ORD-2001", 2, "delivered", "-"),
    ("ORD-2002", 2, "processing", "4 days"),
]


def main() -> None:
    with db.connect() as con:
        con.executescript(db.SCHEMA)
        con.execute("DELETE FROM orders")
        con.executemany(
            "INSERT INTO orders (order_id, tenant_id, status, eta) VALUES (?,?,?,?)", ORDERS)
        con.commit()
    print(f"seeded {len(ORDERS)} orders across 2 tenants (no PII)")


if __name__ == "__main__":
    main()
