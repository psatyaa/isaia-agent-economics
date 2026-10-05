"""The Four Architectural Governance Controls (Mirroring Slide 8)."""

class GovernanceControls:
    def __init__(
        self,
        enable_budget: bool = True,
        max_iterations: int = 3,
        enable_routing: bool = True,
        enable_caching: bool = True,
        enable_compaction: bool = True
    ):
        self.enable_budget = enable_budget
        self.max_iterations = max_iterations
        self.enable_routing = enable_routing
        self.enable_caching = enable_caching
        self.enable_compaction = enable_compaction

    def select_model(self, task_phase: str) -> str:
        """Control 2: Model Routing.
        Routes intent parsing, tool selection, and formatting to SLM (8B).
        Reserves Frontier (70B) for complex synthesis.
        """
        if not self.enable_routing:
            return "frontier"
        if task_phase in ["intent_parsing", "tool_selection", "error_triage"]:
            return "slm"
        return "frontier"

    def compact_context(self, raw_tool_output: str, tool_name: str) -> str:
        """Control 4: Context Compaction.
        Prunes raw JSON stack dumps & voluminous inventory arrays after the Observe phase.
        Retains distilled error codes and resource pointers.
        """
        if not self.enable_compaction:
            return raw_tool_output
        
        # Pruning HTTP 404 stack dumps
        if "HTTP/1.1 404" in raw_tool_output or "SubscriptionNotFound" in raw_tool_output:
            return "[COMPACTED_OBSERVE: query_cost_api returned HTTP 404. ErrorCode: 'SubscriptionNotFound'. Detail: Subscription migrated in IAM to CORP-FIN-V2.]"
        
        # Pruning large 8KB inventory dumps
        if "Microsoft.Compute/virtualMachines" in raw_tool_output and len(raw_tool_output) > 500:
            return f"[COMPACTED_OBSERVE: list_resources returned 44 VMs. Top pool: 'rg-infra-01' through '05'. Full 8KB JSON payload pruned from active prompt.]"
            
        return raw_tool_output

    def check_circuit_breaker(self, current_iteration: int) -> bool:
        """Control 1: Execution Budgets.
        Halts runaway loops when the iteration ceiling is reached.
        """
        if not self.enable_budget:
            return False  # Unbounded
        return current_iteration >= self.max_iterations
