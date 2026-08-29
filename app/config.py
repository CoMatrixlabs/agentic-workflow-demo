"""Runtime settings for the customer-operations multi-agent workflow.

Baseline posture is SAFE and PII-free: the billing sub-agent reaches only non-sensitive
order/status data, the comms sub-agent may only send an internal, allow-listed summary
(held for human approval), sub-agents share ONLY non-sensitive fields through the shared
workflow state, and generation temperature is low for the tool-driving paths. The
vulnerable demo branch wires the agents to customer PII and flips these controls so one
agent's data leaks out through another.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2          # low for tool-driving / effectful paths
    max_tool_iterations: int = 6

    # --- data-boundary controls (safe defaults) ---
    require_tool_approval: bool = True        # human-in-the-loop for send / effectful tools
    enforce_tenant_scope: bool = True         # every DB read is filtered by the caller's tenant
    share_full_context: bool = False          # sub-agents share ONLY minimal, non-sensitive context

    # comms sub-agent may only send to this internal, allow-listed recipient
    allowed_recipients: tuple[str, ...] = ("ops-notify@internal.example",)

    log_level: str = "INFO"

    class Config:
        env_prefix = "CUSTOMER_OPS_"


settings = Settings()
