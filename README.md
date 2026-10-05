# Autonomous Agent Inference Economics & Governance Harness

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/psatyaa/isaia-agent-economics/blob/main/demo_notebook.ipynb)
[![Interactive Briefing](https://img.shields.io/badge/Demo_Briefing-GitHub_Pages-blue.svg)](https://psatyaa.github.io/isaia-agent-economics/)
[![IEEE ISAIA 2026](https://img.shields.io/badge/IEEE_ISAIA_2026-Workshop_Artifact-darkred.svg)](https://www.ieeeisaia.com)

Companion live demonstration repository for the **IEEE ISAIA 2026** presentation:
> **"Beyond the Chatbot: Architecture, Autonomy, and Inference Economics"**  
> *Satya Prakash, Rohan Shahane, Dr. Avimanyou Vatsa*  
> Deep Chain (DC) Lab · Fairleigh Dickinson University

---

## 🎯 Overview & Incident Case Study
This repository provides an interactive demonstration of why unconstrained autonomous LLM loops fail under real-world infrastructure errors, and how four architectural controls eliminate **88.8% of wasted inference tokens**.

* **Interactive Problem Briefing:** [Explore the Incident & Architecture on GitHub Pages](https://psatyaa.github.io/isaia-agent-economics/)
* **1-Click Live Harness:** [Open in Google Colab](https://colab.research.google.com/github/psatyaa/isaia-agent-economics/blob/main/demo_notebook.ipynb)

---

## 🔬 Key Comparisons Demonstrated

| Dimension | Run A: Unconstrained (Slide 7) | Run B: Governed (Slides 8 & 9) |
| :--- | :--- | :--- |
| **Model Tier** | Frontier 70B on every turn | SLM 8B for triage, Frontier for reasoning |
| **Iteration Limit** | Unbounded (infinite retries) | `max_iterations = 3` (Circuit breaker) |
| **Context Handling** | Full stack traces & raw 8KB JSON retained | Context compaction (stack traces pruned) |
| **Total Ingested Tokens** | **19,130 Tokens** | **2,150 Tokens** (**-88.8%**) |
| **Task Outcome** | Unresolved / Budget Burned | Controlled Exit (Structured Handoff Card) |

---

## 🚀 Running Locally
```bash
git clone https://github.com/psatyaa/isaia-agent-economics.git
cd isaia-agent-economics
pip install -r requirements.txt
python -c "from src.agent_loop import AgentHarness; from src.controls import GovernanceControls; print(AgentHarness(GovernanceControls()).run_governed()['handoff_card'])"
```
