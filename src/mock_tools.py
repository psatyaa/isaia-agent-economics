"""Mock enterprise cloud billing and inventory tools with deterministic failure injection."""
import json
from .config import DEFAULT_TARGET_SUBSCRIPTION, MIGRATED_SUBSCRIPTION

def query_cost_api(subscription_id: str, date_range: str = "last-7-days") -> str:
    """Queries the enterprise cloud cost management API.
    Injects a deterministic HTTP 404 when querying the outdated subscription ID.
    """
    if subscription_id == DEFAULT_TARGET_SUBSCRIPTION:
        # Injected failure: Subscription was migrated/renamed in enterprise IAM
        stack_trace = f"""HTTP/1.1 404 Not Found
Date: Mon, 05 Oct 2026 08:12:44 GMT
Content-Type: application/json; charset=utf-8
X-Billing-Correlation-ID: 7a8f9b22-8391-4e78-b112-9844e1f7d23a

{{
  "error": {{
    "code": "SubscriptionNotFound",
    "message": "Subscription ID '{subscription_id}' does not exist or was decommissioned during IAM migration.",
    "target": "Microsoft.CostManagement/query",
    "details": [
      {{
        "code": "ResourceRenamedOrMoved",
        "message": "Active enterprise accounts moved to tenant 'CORP-FIN-V2' on 2026-10-02T14:00Z.",
        "innererror": {{
          "stack_trace": "Traceback (most recent call last):\\n  File '/opt/billing/gateway/router.py', line 142, in route_request\\n    sub = registry.get_active_sub(sub_id)\\n  File '/opt/billing/gateway/registry.py', line 89, in get_active_sub\\n    raise SubscriptionNotFoundError(f'Decommissioned pointer: {{sub_id}}')\\nSubscriptionNotFoundError: Decommissioned pointer: {subscription_id}"
        }}
      }}
    ]
  }}
}}"""
        return stack_trace
    elif subscription_id == MIGRATED_SUBSCRIPTION:
        return json.dumps({
            "status": "success",
            "subscription_id": MIGRATED_SUBSCRIPTION,
            "billing_period": date_range,
            "total_spend_usd": 48250.00,
            "previous_period_usd": 34950.00,
            "variance_percent": "+38.05%",
            "top_cost_contributors": [
                {"resource_group": "rg-llm-training-evals", "service": "GPU Cluster (NC24ads_A100)", "cost_usd": 14200.00, "variance": "+185%"},
                {"resource_group": "rg-streaming-kafka", "service": "EventHub / Kafka", "cost_usd": 6800.00, "variance": "+12%"},
                {"resource_group": "rg-core-databases", "service": "CosmosDB / Multi-region", "cost_usd": 5100.00, "variance": "-2%"}
            ],
            "root_cause_summary": "Runaway unbudgeted GPU training jobs spawned in 'rg-llm-training-evals' over the weekend without automated spot termination."
        }, indent=2)
    else:
        return json.dumps({"error": "UnknownSubscription", "message": f"Subscription '{subscription_id}' unrecognized."})

def list_resources(resource_group: str = "all") -> str:
    """Returns an unfiltered inventory dump of cloud resources (~8KB noisy JSON payload)."""
    items = []
    for i in range(1, 45):
        items.append({
            "id": f"/subscriptions/{DEFAULT_TARGET_SUBSCRIPTION}/resourceGroups/rg-infra-{i:02d}/providers/Microsoft.Compute/virtualMachines/vm-worker-{i:03d}",
            "name": f"vm-worker-{i:03d}",
            "type": "Microsoft.Compute/virtualMachines",
            "location": "eastus2",
            "tags": {"Environment": "Production", "CostCenter": "CC-9012", "Owner": f"team-core-{i % 5}"},
            "properties": {
                "hardwareProfile": {"vmSize": "Standard_D4s_v5"},
                "provisioningState": "Succeeded",
                "osProfile": {"computerName": f"worker-{i:03d}", "adminUsername": "azureuser"},
                "networkProfile": {"networkInterfaces": [{"id": f"/subscriptions/sub/nic-{i:03d}"}]}
            }
        })
    return json.dumps({"value": items, "count": len(items)}, indent=2)

def search_runbook(topic: str) -> str:
    """Searches FinOps remediation runbooks."""
    runbooks = {
        "cost-spike": "FinOps SOP #104: For unexpected spend anomalies exceeding 25%, verify IAM subscription mapping first, inspect top GPU/Compute clusters, and enforce tags.",
        "gpu-orphan": "FinOps SOP #89: Terminate unattached GPU nodes in non-prod pools. Contact ML engineering owner."
    }
    return runbooks.get(topic, "No matching SOP found in catalog.")
