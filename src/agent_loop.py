"""Plan-Act-Observe-Reflect (PAOR) Agent Execution Engine."""
import json
from .mock_tools import query_cost_api, list_resources, search_runbook
from .controls import GovernanceControls
from .telemetry import TelemetryTracker

class AgentHarness:
    def __init__(self, controls: GovernanceControls, mode: str = "replay"):
        self.controls = controls
        self.mode = mode
        self.telemetry = TelemetryTracker()

    def run_unconstrained(self) -> dict:
        """Runs the unconstrained agent loop (reproducing Slide 7)."""
        self.telemetry = TelemetryTracker()
        
        # Load deterministic replay trace
        from pathlib import Path
        trace_file = Path(__file__).parent.parent / "data" / "replay_traces.json"
        with open(trace_file) as f:
            data = json.load(f)["unconstrained"]
            
        for step in data:
            self.telemetry.record_turn(
                turn_num=step["turn"],
                phase=step["phase"],
                model_tier=step["model_tier"],
                in_tokens=step["in_tokens"],
                out_tokens=step["out_tokens"],
                action_summary=step["action"],
                status=step["status"]
            )
            
        return {
            "status": "UNRESOLVED / BUDGET EXHAUSTED",
            "total_in_tokens": self.telemetry.cumulative_in_tokens,
            "total_tokens": self.telemetry.cumulative_in_tokens + self.telemetry.cumulative_out_tokens,
            "cost_usd": self.telemetry.cumulative_cost_usd,
            "turns": self.telemetry.turns
        }

    def run_governed(self) -> dict:
        """Runs the governed agent loop with the 4 controls (reproducing Slides 8 & 9)."""
        self.telemetry = TelemetryTracker()
        
        from pathlib import Path
        trace_file = Path(__file__).parent.parent / "data" / "replay_traces.json"
        with open(trace_file) as f:
            data = json.load(f)["governed"]
            
        for step in data:
            self.telemetry.record_turn(
                turn_num=step["turn"],
                phase=step["phase"],
                model_tier=step["model_tier"],
                in_tokens=step["in_tokens"],
                out_tokens=step["out_tokens"],
                action_summary=step["action"],
                status=step["status"]
            )
            
        handoff_card = self.telemetry.generate_handoff_card(
            trigger_reason=f"max_iterations: {self.controls.max_iterations}",
            root_cause="query_cost_api returned HTTP 404 (IAM subscription pointer missing)",
            recommended_fix="Update subscription pointer to 'sub-prod-v2-analytics' in cloud governance catalog",
            tokens_saved=16980
        )
        
        return {
            "status": "CONTROLLED ESCALATION (SUCCESSFUL HANDOFF)",
            "total_in_tokens": self.telemetry.cumulative_in_tokens,
            "total_tokens": self.telemetry.cumulative_in_tokens + self.telemetry.cumulative_out_tokens,
            "cost_usd": self.telemetry.cumulative_cost_usd,
            "turns": self.telemetry.turns,
            "handoff_card": handoff_card
        }
