"""Configuration constants, pricing tables, and model definitions for ISAIA Agent Economics harness."""

# Model definitions
MODEL_FRONTIER = "llama-3.1-70b-versatile" # High-capability reasoning tier
MODEL_SLM = "llama-3.1-8b-instant"          # Fast, cost-efficient small language model tier

# List-price equivalent rates (per 1M tokens) based on industry frontier vs SLM baselines
PRICING = {
    "frontier": {
        "input_per_1m": 3.00,   # $3.00 / 1M input tokens
        "output_per_1m": 15.00  # $15.00 / 1M output tokens
    },
    "slm": {
        "input_per_1m": 0.20,   # $0.20 / 1M input tokens
        "output_per_1m": 0.20   # $0.20 / 1M output tokens
    }
}

# Governance default boundaries (matching Slide 8)
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_TARGET_SUBSCRIPTION = "sub-prod-analytics-01"
MIGRATED_SUBSCRIPTION = "sub-prod-v2-analytics"
