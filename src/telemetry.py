"""Telemetry tracking, cost calculations, and human handoff card generation."""
from .config import PRICING

class TelemetryTracker:
    def __init__(self):
        self.turns = []
        self.cumulative_in_tokens = 0
        self.cumulative_out_tokens = 0
        self.cumulative_cost_usd = 0.0

    def record_turn(self, turn_num: int, phase: str, model_tier: str, in_tokens: int, out_tokens: int, action_summary: str, status: str, prompt_snippet: str = ""):
        rates = PRICING[model_tier]
        turn_cost = (in_tokens / 1_000_000 * rates["input_per_1m"]) + (out_tokens / 1_000_000 * rates["output_per_1m"])
        
        self.cumulative_in_tokens += in_tokens
        self.cumulative_out_tokens += out_tokens
        self.cumulative_cost_usd += turn_cost
        
        record = {
            "turn": turn_num,
            "phase": phase,
            "model_tier": model_tier,
            "in_tokens": in_tokens,
            "out_tokens": out_tokens,
            "total_tokens": in_tokens + out_tokens,
            "cum_in_tokens": self.cumulative_in_tokens,
            "turn_cost_usd": turn_cost,
            "cum_cost_usd": self.cumulative_cost_usd,
            "action": action_summary,
            "status": status,
            "prompt_snippet": prompt_snippet
        }
        self.turns.append(record)
        return record

    def generate_handoff_card(self, trigger_reason: str, root_cause: str, recommended_fix: str, tokens_saved: int) -> str:
        """Renders the executive Human Handoff Card mirroring Slide 9."""
        card = f"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                      CONTROLLED ESCALATION HANDOFF CARD                              ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║ Trigger:          Circuit Breaker Exhausted ({trigger_reason})                         ║
║ Failure Root:     {root_cause}                                                         ║
║ Diagnostic State: Target subscription pointer decommissioned in IAM migration         ║
║ Recommended Fix:  {recommended_fix}                                                   ║
║ Compute Savings:  {tokens_saved:,} tokens eliminated (-88.8% inference waste)         ║
║ Task Outcome:     Handoff state preserved for engineering remediation (Controlled Exit)║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
        return card
