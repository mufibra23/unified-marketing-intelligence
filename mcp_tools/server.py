"""
MCP Tools Server for Unified Marketing Intelligence Platform.
12 tools wrapping FastAPI endpoints for agent consumption.

Run: python -m mcp_tools.server
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

# Use TestClient for in-process calls (no need for running server)
_client = TestClient(app)


def _call_api(endpoint: str, params: dict | None = None) -> dict:
    """Call the FastAPI endpoint and return parsed JSON."""
    try:
        r = _client.get(endpoint, params=params)
        if r.status_code == 200:
            return {"success": True, "data": r.json()}
        else:
            return {
                "success": False,
                "isError": True,
                "error_category": "not_found" if r.status_code == 404 else "server_error",
                "retryable": r.status_code >= 500,
                "message": r.json().get("detail", f"HTTP {r.status_code}"),
            }
    except Exception as e:
        return {
            "success": False,
            "isError": True,
            "error_category": "connection_error",
            "retryable": True,
            "message": str(e),
        }


# ─────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# ─────────────────────────────────────────────

def query_attribution_summary() -> str:
    return json.dumps(_call_api("/api/v1/attribution/summary"), indent=2)


def query_attribution_channel(channel_name: str) -> str:
    return json.dumps(_call_api(f"/api/v1/attribution/channel/{channel_name}"), indent=2)


def query_top_leads(n: int = 20, min_score: float = 0) -> str:
    return json.dumps(_call_api("/api/v1/leads/top", {"n": n, "min_score": min_score}), indent=2)


def query_lead_detail(lead_id: str) -> str:
    return json.dumps(_call_api(f"/api/v1/leads/{lead_id}"), indent=2)


def query_segments_overview() -> str:
    return json.dumps(_call_api("/api/v1/segments/overview"), indent=2)


def query_segment_customers(segment_id: int, limit: int = 50) -> str:
    return json.dumps(_call_api(f"/api/v1/segments/{segment_id}/customers", {"limit": limit}), indent=2)


def query_sentiment_summary() -> str:
    return json.dumps(_call_api("/api/v1/sentiment/summary"), indent=2)


def query_sentiment_alerts(severity: str | None = None) -> str:
    params = {"severity": severity} if severity else None
    return json.dumps(_call_api("/api/v1/sentiment/alerts", params), indent=2)


def query_daily_metrics(
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    limit: int = 100,
) -> str:
    params = {"limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if channel:
        params["channel"] = channel
    return json.dumps(_call_api("/api/v1/metrics/daily", params), indent=2)


def query_anomalies() -> str:
    return json.dumps(_call_api("/api/v1/metrics/anomalies"), indent=2)


def write_report(title: str, content: str) -> str:
    return json.dumps({
        "success": True,
        "report": {"title": title, "content": content, "format": "markdown"},
    }, indent=2)


def verify_fact(claim: str, data_source: str) -> str:
    source_map = {
        "attribution": "/api/v1/attribution/summary",
        "leads": "/api/v1/leads/top",
        "segments": "/api/v1/segments/overview",
        "sentiment": "/api/v1/sentiment/summary",
        "metrics": "/api/v1/metrics/anomalies",
    }
    endpoint = source_map.get(data_source)
    if not endpoint:
        return json.dumps({
            "success": False, "isError": True,
            "error_category": "invalid_input", "retryable": False,
            "message": f"Unknown data source: {data_source}. Use: {list(source_map.keys())}",
        })
    result = _call_api(endpoint)
    return json.dumps({
        "success": True, "claim": claim, "data_source": data_source,
        "reference_data": result.get("data", {}),
        "note": "Compare the claim against the reference data to determine accuracy.",
    }, indent=2)


# Tool dispatcher
TOOL_FUNCTIONS = {
    "query_attribution_summary": query_attribution_summary,
    "query_attribution_channel": query_attribution_channel,
    "query_top_leads": query_top_leads,
    "query_lead_detail": query_lead_detail,
    "query_segments_overview": query_segments_overview,
    "query_segment_customers": query_segment_customers,
    "query_sentiment_summary": query_sentiment_summary,
    "query_sentiment_alerts": query_sentiment_alerts,
    "query_daily_metrics": query_daily_metrics,
    "query_anomalies": query_anomalies,
    "write_report": write_report,
    "verify_fact": verify_fact,
}


def call_tool(tool_name: str, **kwargs) -> str:
    fn = TOOL_FUNCTIONS.get(tool_name)
    if not fn:
        return json.dumps({
            "success": False, "isError": True,
            "error_category": "unknown_tool", "retryable": False,
            "message": f"Unknown tool: {tool_name}. Available: {list(TOOL_FUNCTIONS.keys())}",
        })
    try:
        return fn(**kwargs)
    except Exception as e:
        return json.dumps({
            "success": False, "isError": True,
            "error_category": "execution_error", "retryable": True,
            "message": str(e),
        })


if __name__ == "__main__":
    print("Testing all 12 MCP tools...")
    tests = [
        ("query_attribution_summary", {}),
        ("query_attribution_channel", {"channel_name": "paid_search"}),
        ("query_top_leads", {"n": 3}),
        ("query_lead_detail", {"lead_id": "LEAD-00001"}),
        ("query_segments_overview", {}),
        ("query_segment_customers", {"segment_id": 0, "limit": 3}),
        ("query_sentiment_summary", {}),
        ("query_sentiment_alerts", {"severity": "high"}),
        ("query_daily_metrics", {"channel": "email", "limit": 3}),
        ("query_anomalies", {}),
        ("write_report", {"title": "Test", "content": "# Test"}),
        ("verify_fact", {"claim": "Paid search has highest ROI", "data_source": "attribution"}),
    ]
    passed = 0
    for name, kwargs in tests:
        result = json.loads(call_tool(name, **kwargs))
        ok = result.get("success", False)
        if ok: passed += 1
        print(f"  {'PASS' if ok else 'FAIL'} {name}")
    print(f"\n{passed}/12 tools passing")
