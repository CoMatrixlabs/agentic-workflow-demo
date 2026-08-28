"""Runtime settings for the customer-operations multi-agent workflow.

Baseline posture is SAFE: sub-agents only exchange non-sensitive fields through the shared
workflow state, PII is masked before anything crosses an agent boundary, the comms agent's
outbound send is human-approved and allow-listed, and generation temperature is low for the
tool-driving paths. The vulnerable demo branch flips these to let one agent's data leak out
through another.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2          # low for tool-driving / effectful paths
    max_tool_iterations: int = 6

    # --- data-boundary controls (safe defaults) ---
    require_tool_approval: bool = True        # human-in-the-loop for send / effectful tools
    mask_pii: bool = True                     # mask SSN / bank before anything crosses agents
    enforce_tenant_scope: bool = True         # every DB read is filtered by the caller's tenant
    share_full_context: bool = False          # sub-agents share ONLY masked, minimal context

    # comms sub-agent may only send to this internal, allow-listed recipient
    allowed_recipients: tuple[str, ...] = ("ops-notify@internal.example",)

    log_level: str = "INFO"

    class Config:
        env_prefix = "CUSTOMER_OPS_"


settings = Settings()
