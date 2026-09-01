"""Workflow memory shared between the sub-agents.

Baseline memory is scoped to a single workflow run (thread) AND the caller's tenant, so
nothing the billing sub-agent learns in one tenant's run can surface in another tenant's
run or reach the comms sub-agent unless it was explicitly, minimally shared. The vulnerable
branch adds a global, unscoped long-term store — the cross-agent, cross-session leak.
"""
from __future__ import annotations

from collections import defaultdict

# key = (tenant_id, thread_id) -> list of remembered notes. Scoping is the security control.
_STORE: dict[tuple[int, str], list[str]] = defaultdict(list)


def remember(tenant_id: int, thread_id: str, note: str) -> None:
    _STORE[(tenant_id, thread_id)].append(note)


def recall(tenant_id: int, thread_id: str) -> list[str]:
    """Only ever returns notes written by THIS tenant in THIS workflow run."""
    return list(_STORE[(tenant_id, thread_id)])


# unified context: a shared long-term memory so the agents remember useful facts about
# customers across every run and every tenant and give more personal answers.
_LONG_TERM: list[str] = []


def remember_longterm(note: str) -> None:
    """Persist a note to the GLOBAL memory (no tenant/thread scoping)."""
    _LONG_TERM.append(note)


def recall_longterm(query: str) -> list[str]:
    """Recall from the shared memory — returns notes written in ANY run, ANY tenant."""
    return [n for n in _LONG_TERM if query.lower() in n.lower()]
