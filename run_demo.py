#!/usr/bin/env python3
"""CLI runner for testing and presenting the ISAIA Agent Economics demo."""

import os
import sys
import argparse
from tabulate import tabulate

from src.controls import GovernanceControls
from src.agent_loop import AgentHarness

def parse_args():
    parser = argparse.ArgumentParser(description="ISAIA 2026: Agent Economics Demo Runner")
    parser.add_argument(
        "--mode",
        choices=["replay", "live"],
        default="replay",
        help="Execution mode: 'replay' (0-key, deterministic) or 'live' (real Groq LLM API)",
    )
    parser.add_argument(
        "--key",
        default=None,
        help="Groq API key (optional if GROQ_API_KEY env var is set)",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    mode = args.mode
    api_key = args.key or os.environ.get("GROQ_API_KEY")

    print("\n" + "=" * 80)
    print("  IEEE ISAIA 2026: INFERENCE ECONOMICS & GOVERNANCE DEMO")
    print(f"  ACTIVE MODE: {mode.upper()} {'(Live Groq LLM)' if mode == 'live' else '(Deterministic 0-Key Replay)'}")
    print("=" * 80)

    # 1. RUN A: UNCONSTRAINED
    print("\n[STEP 1/2] RUNNING A: UNCONSTRAINED AUTONOMOUS LOOP (SLIDE 7)...")
    ctrls_a = GovernanceControls(enable_budget=False, enable_routing=False, enable_compaction=False)
    harness_a = AgentHarness(ctrls_a, mode=mode, api_key=api_key)
    res_a = harness_a.run_unconstrained()

    table_a = []
    for t in res_a["turns"]:
        row = [
            f"Turn {t['turn']}",
            t["phase"],
            t["model_tier"].upper(),
            f"{t['in_tokens']:,}",
            f"{t['cum_in_tokens']:,}",
            f"${t['turn_cost_usd']:.4f}",
            t["status"],
        ]
        if mode == 'live' and 'prompt_snippet' in t:
            row.append(t['prompt_snippet'])
        table_a.append(row)
    
    headers = ["Turn", "Phase", "Tier", "Input Tokens", "Accum. In", "Turn Cost", "Status"]
    if mode == 'live':
        headers.append("Prompt Snippet")
    print(tabulate(table_a, headers=headers, tablefmt="fancy_grid"))
    print(f"Run A Workload: {res_a['total_in_tokens']:,} Input Tokens | Spend: ${res_a['cost_usd']:.4f}")
    print(f"Run A Outcome:  {res_a['status']}")

    # 2. RUN B: GOVERNED
    print("\n" + "-" * 80)
    print("[STEP 2/2] RUNNING B: GOVERNED LOOP WITH 4 CONTROLS (SLIDES 8 & 9)...")
    ctrls_b = GovernanceControls(enable_budget=True, max_iterations=3, enable_routing=True, enable_compaction=True)
    harness_b = AgentHarness(ctrls_b, mode=mode, api_key=api_key)
    res_b = harness_b.run_governed()

    table_b = []
    for t in res_b["turns"]:
        row = [
            f"Turn {t['turn']}",
            t["phase"],
            t["model_tier"].upper(),
            f"{t['in_tokens']:,}",
            f"{t['cum_in_tokens']:,}",
            f"${t['turn_cost_usd']:.4f}",
            t["status"],
        ]
        if mode == 'live' and 'prompt_snippet' in t:
            row.append(t['prompt_snippet'])
        table_b.append(row)
    print(tabulate(table_b, headers=headers, tablefmt="fancy_grid"))
    print(f"Run B Workload: {res_b['total_in_tokens']:,} Input Tokens | Spend: ${res_b['cost_usd']:.4f}")
    print(f"Run B Outcome:  {res_b['status']}")

    print("\n" + res_b["handoff_card"])

    # 3. SUMMARY
    tok_saved = res_a["total_in_tokens"] - res_b["total_in_tokens"]
    savings_pct = (tok_saved / res_a["total_in_tokens"]) * 100 if res_a["total_in_tokens"] > 0 else 0
    print("\n" + "=" * 80)
    print("  EXECUTIVE SUMMARY (SLIDE 10)")
    print(f"  • Compute Waste Avoided: {tok_saved:,} (-{savings_pct:.1f}% reduction)")
    print(f"  • Cost Differential:     ${res_a['cost_usd']:.4f} (Unresolved) vs ${res_b['cost_usd']:.4f} (Governed Handoff)")
    print("=" * 80 + "\n")

    # 4. EXPORT LIVE TRACES FOR GITHUB PAGES
    import json
    from pathlib import Path
    if mode == "live":
        trace_path = Path(__file__).parent / "data" / "live_traces.json"
        live_data = {
            "unconstrained": res_a["turns"],
            "governed": res_b["turns"]
        }
        with open(trace_path, "w") as f:
            json.dump(live_data, f, indent=2)
        print(f"
[+] Saved live telemetry to {trace_path} for GitHub Pages UI.
")

if __name__ == "__main__":
    main()
