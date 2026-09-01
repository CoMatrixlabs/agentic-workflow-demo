"""Central PII masking. One place so no sub-agent can accidentally serialize raw fields
into the shared workflow state."""
from __future__ import annotations

from .config import settings

_SENSITIVE = ("ssn", "bank_account")


def _mask(value: str) -> str:
    s = str(value)
    return ("*" * max(0, len(s) - 4)) + s[-4:] if len(s) > 4 else "****"


def mask_record(record: dict) -> dict:
    """Return a copy with sensitive fields masked when masking is enabled."""
    if not settings.mask_pii:
        return dict(record)
    out = dict(record)
    for k in _SENSITIVE:
        if k in out and out[k] is not None:
            out[k] = _mask(out[k])
    return out
