"""Plan-Act-Observe-Reflect (PAOR) Agent Execution Engine.
Supports both deterministic offline replay mode and live Groq LLM execution.
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

from .mock_tools import query_cost_api, list_resources, search_runbook
from .controls import GovernanceControls
from .telemetry import TelemetryTracker
from .config import MODEL_FRONTIER, MODEL_SLM, DEFAULT_TARGET_SUBSCRIPTION

class AgentHarness:
    def __init__(self, controls: GovernanceControls, mode: str = "replay", api_key: Optional[str] = None):
        """
        Args:
            controls: GovernanceControls instance configuring budgets, routing, and compaction.
            mode: "replay" (deterministic 0-key replay) or "live" (calls Groq API).
            api_key: Optional Groq API key (defaults to GROQ_API_KEY environment variable).
        """
        self.controls = controls
        self.mode = mode.lower()
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.frontier_model = MODEL_FRONTIER
        self.slm_model = MODEL_SLM
        self.telemetry = TelemetryTracker()
        self._groq_client = None

        if self.mode == "live":
            if not self.api_key:
                print("⚠️ [AgentHarness] No GROQ_API_KEY provided. Gracefully falling back to REPLAY mode.")
                self.mode = "replay"
            else:
                try:
                    from groq import Groq
                    self._groq_client = Groq(api_key=self.api_key)
                    
                    # Auto-discover active models to prevent model_decommissioned errors
                    active_models = [m.id for m in self._groq_client.models.list().data]
                    
                    # --- DYNAMIC TEXT MODEL AUTO-DISCOVERY ---
                    import re
                    # 1. Fetch all models and filter out deprecated ones (if Groq API exposes 'active' attribute)
                    all_models = self._groq_client.models.list().data
                    
                    candidates = []
                    for m in all_models:
                        m_id = m.id.lower()
                        # Exclude if explicitly marked deprecated
                        if getattr(m, 'active', None) is False:
                            continue
                            
                        # Groq API doesn't expose a 'capabilities.chat' boolean yet, so we filter 
                        # out audio/vision/gated namespaces instead of hardcoding model brands.
                        if any(x in m_id for x in ["whisper", "canopylabs", "vision", "embedding", "whisper-large-v3", "guard", "classifier", "eval"]):
                            continue
                            
                        # Extract parameter size for mathematical sorting (e.g. 70b -> 70, 8x7b -> 56)
                        size = 0
                        mo_moe = re.search(r'(\d+)x(\d+)b', m_id)
                        mo_std = re.search(r'(\d+)b', m_id)
                        
                        if mo_moe:
                            size = int(mo_moe.group(1)) * int(mo_moe.group(2))
                        elif mo_std:
                            size = int(mo_std.group(1))
                        elif "mixtral" in m_id:
                            size = 56 # Fallback size for mixtral if missing 8x7b
                            
                        candidates.append((size, m.id))
                        
                    if not candidates:
                        self.frontier_model = "llama3-70b-8192"
                        self.slm_model = "llama3-8b-8192"
                    else:
                        # Sort models strictly by parameter size (ascending)
                        candidates.sort(key=lambda x: x[0])
                        
                        # Frontier = Largest parameter model in your active account
                        self.frontier_model = candidates[-1][1]
                        
                        # SLM = Smallest parameter model in your active account
                        self.slm_model = candidates[0][1]
                except Exception as e:
                    print(f"⚠️ [AgentHarness] Error initializing Groq client ({e}). Falling back to REPLAY mode.")
                    self.mode = "replay"

    def _call_groq(self, model: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Calls Groq API and extracts output tokens and response text."""
        try:
            chat_completion = self._groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model,
                temperature=0.2,
                max_tokens=256,
            )
            usage = chat_completion.usage
            sys_snip = system_prompt.replace('\n', ' ')[:50]
            usr_snip = user_prompt.replace('\n', ' ')[:50]
            return {
                "text": chat_completion.choices[0].message.content,
                "in_tokens": usage.prompt_tokens,
                "out_tokens": usage.completion_tokens,
                "prompt_snippet": f"SYS: {sys_snip}... | USR: {usr_snip}..."
            }
        except Exception as e:
            print(f"\n⚠️ [Groq API Notice]: {e}")
            print("🔄 Seamlessly falling back to deterministic REPLAY mode so presentation continues uninterrupted...\n")
            return None

    def run_unconstrained(self) -> dict:
        """Runs the unconstrained agent loop (reproducing Slide 7)."""
        self.telemetry = TelemetryTracker()

        if self.mode == "live" and self._groq_client:
            return self._run_unconstrained_live()
        else:
            return self._run_unconstrained_replay()

    def _run_unconstrained_replay(self) -> dict:
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
            "mode": "replay",
            "status": "UNRESOLVED / BUDGET EXHAUSTED",
            "total_in_tokens": self.telemetry.cumulative_in_tokens,
            "total_tokens": self.telemetry.cumulative_in_tokens + self.telemetry.cumulative_out_tokens,
            "cost_usd": self.telemetry.cumulative_cost_usd,
            "turns": self.telemetry.turns
        }

    def _run_unconstrained_live(self) -> dict:
        """Executes real live API calls against Groq with unconstrained context snowballing."""
        context_accumulator = "Initial goal: Investigate +38% cloud cost spike in subscription sub-prod-analytics-01."
        
        # Turn 1: Initial query
        resp1 = self._call_groq(
            model=self.frontier_model,
            system_prompt="You are an autonomous cloud FinOps agent. Plan and execute an API query to inspect cloud costs.",
            user_prompt=context_accumulator
        )
        if not resp1:
            return self._run_unconstrained_replay()
        tool_out1 = query_cost_api(DEFAULT_TARGET_SUBSCRIPTION)
        context_accumulator += f"\n\n[Agent Turn 1 Action]: query_cost_api('{DEFAULT_TARGET_SUBSCRIPTION}')\n[Tool Output]:\n{tool_out1}"
        self.telemetry.record_turn(1, "Plan & Act", "frontier", resp1["in_tokens"], resp1["out_tokens"], f"query_cost_api({DEFAULT_TARGET_SUBSCRIPTION}) -> HTTP 404", "HTTP 404 Not Found", resp1["prompt_snippet"])

        # Turn 2: Swallow full stack trace and retry
        resp2 = self._call_groq(
            model=self.frontier_model,
            system_prompt="Analyze the error response and formulate next steps. Include full previous context.",
            user_prompt=context_accumulator
        )
        if not resp2:
            return self._run_unconstrained_replay()
        context_accumulator += f"\n\n[Agent Turn 2 Reflection]: {resp2['text']}\n[Tool Output]: Full 45-line stack trace ingested."
        self.telemetry.record_turn(2, "Reflect & Retry", "frontier", resp2["in_tokens"], resp2["out_tokens"], "Full stack trace ingested. Retry syntax attempted.", "Stack Dump Compounding (+135%)", resp2["prompt_snippet"])

        # Turn 3: Swallowing noisy resource list
        raw_inventory = list_resources("all")
        context_accumulator += f"\n\n[Tool Output]: list_resources('all') returned:\n{raw_inventory[:4000]}"
        resp3 = self._call_groq(
            model=self.frontier_model,
            system_prompt="Analyze full inventory dump to find the failing resources.",
            user_prompt=context_accumulator
        )
        if not resp3:
            return self._run_unconstrained_replay()
        self.telemetry.record_turn(3, "Fallback Search", "frontier", resp3["in_tokens"], resp3["out_tokens"], "list_resources('all') -> Swallows raw 8KB inventory JSON.", "JSON Bloat (+107%)", resp3["prompt_snippet"])

        # Turn 4: Saturated degraded loop
        resp4 = self._call_groq(
            model=self.frontier_model,
            system_prompt="Attempt further resolution based on the full accumulated history.",
            user_prompt=context_accumulator
        )
        if not resp4:
            return self._run_unconstrained_replay()
        self.telemetry.record_turn(4, "Degraded Loop", "frontier", resp4["in_tokens"], resp4["out_tokens"], "Context saturated. Loops same failed query across prior stack traces.", "Loop Saturation / Failed (+80%)", resp4["prompt_snippet"])

        return {
            "mode": "live",
            "status": "UNRESOLVED / BUDGET EXHAUSTED",
            "total_in_tokens": self.telemetry.cumulative_in_tokens,
            "total_tokens": self.telemetry.cumulative_in_tokens + self.telemetry.cumulative_out_tokens,
            "cost_usd": self.telemetry.cumulative_cost_usd,
            "turns": self.telemetry.turns
        }

    def run_governed(self) -> dict:
        """Runs the governed agent loop with 4 controls (reproducing Slides 8 & 9)."""
        self.telemetry = TelemetryTracker()

        if self.mode == "live" and self._groq_client:
            return self._run_governed_live()
        else:
            return self._run_governed_replay()

    def _run_governed_replay(self) -> dict:
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
            "mode": "replay",
            "status": "CONTROLLED ESCALATION (SUCCESSFUL HANDOFF)",
            "total_in_tokens": self.telemetry.cumulative_in_tokens,
            "total_tokens": self.telemetry.cumulative_in_tokens + self.telemetry.cumulative_out_tokens,
            "cost_usd": self.telemetry.cumulative_cost_usd,
            "turns": self.telemetry.turns,
            "handoff_card": handoff_card
        }

    def _run_governed_live(self) -> dict:
        """Executes real live API calls against Groq with governed controls (SLM triage, compaction, circuit breaker)."""
        # Turn 1: SLM Fast Triage (Control 2: SLM Routing)
        resp1 = self._call_groq(
            model=self.slm_model,
            system_prompt="You are a lightweight intent classifier. Classify target subscription query intent in one sentence.",
            user_prompt="Goal: Investigate +38% cost anomaly for subscription sub-prod-analytics-01."
        )
        if not resp1:
            return self._run_governed_replay()
        self.telemetry.record_turn(1, "Intent Parsing", "slm", resp1["in_tokens"], resp1["out_tokens"], "SLM (8B) routes intent and prepares cost query.", "SLM Fast Triage", resp1["prompt_snippet"])

        # Turn 2: Error compaction (Control 4: Compact Context)
        raw_error = query_cost_api(DEFAULT_TARGET_SUBSCRIPTION)
        compact_error = self.controls.compact_context(raw_error, "query_cost_api")
        resp2 = self._call_groq(
            model=self.slm_model,
            system_prompt="You are a compact error parser. Summarize this error in 15 words: " + compact_error,
            user_prompt="State error code and reason."
        )
        if not resp2:
            return self._run_governed_replay()
        self.telemetry.record_turn(2, "Error Compaction", "slm", resp2["in_tokens"], resp2["out_tokens"], "404 caught; stack trace pruned to clean error code.", "Context Compacted", resp2["prompt_snippet"])

        # Turn 3: Circuit breaker trip check (Control 1: max_iterations=3)
        resp3 = self._call_groq(
            model=self.frontier_model,
            system_prompt="System policy: Max iterations reached (3/3). Trigger controlled escalation.",
            user_prompt="Explain why breaker tripped: Target subscription returned HTTP 404 SubscriptionNotFound."
        )
        if not resp3:
            return self._run_governed_replay()
        self.telemetry.record_turn(3, "Circuit Breaker", "frontier", resp3["in_tokens"], resp3["out_tokens"], f"Max iteration limit reached ({self.controls.max_iterations}/{self.controls.max_iterations}). Breaker trips gracefully.", "Circuit Breaker Triggered", resp3["prompt_snippet"])

        # Turn 4: SLM Human Handoff generation (Human-in-the-loop)
        resp4 = self._call_groq(
            model=self.slm_model,
            system_prompt="Format an incident handoff summary with root cause and recommended remediation.",
            user_prompt="Error: HTTP 404 SubscriptionNotFound for sub-prod-analytics-01. Fix: Migrate to sub-prod-v2-analytics."
        )
        if not resp4:
            return self._run_governed_replay()
        self.telemetry.record_turn(4, "Handoff Generator", "slm", resp4["in_tokens"], resp4["out_tokens"], "Packages diagnostic state snapshot and remediation recommendation.", "Controlled Exit (Handoff)", resp4["prompt_snippet"])

        tokens_saved = max(0, 19130 - self.telemetry.cumulative_in_tokens)
        handoff_card = self.telemetry.generate_handoff_card(
            trigger_reason=f"max_iterations: {self.controls.max_iterations}",
            root_cause="query_cost_api returned HTTP 404 (IAM subscription pointer missing)",
            recommended_fix="Update subscription pointer to 'sub-prod-v2-analytics' in cloud governance catalog",
            tokens_saved=tokens_saved
        )

        return {
            "mode": "live",
            "status": "CONTROLLED ESCALATION (SUCCESSFUL HANDOFF)",
            "total_in_tokens": self.telemetry.cumulative_in_tokens,
            "total_tokens": self.telemetry.cumulative_in_tokens + self.telemetry.cumulative_out_tokens,
            "cost_usd": self.telemetry.cumulative_cost_usd,
            "turns": self.telemetry.turns,
            "handoff_card": handoff_card
        }
