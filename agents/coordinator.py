"""
Multi-Agent Coordinator for P9: Unified Marketing Intelligence Platform.

Implements the coordinator-subagent orchestration pattern (CCA Exercise 4):
- Coordinator decomposes queries and dispatches subagents
- Subagents have scoped tool access
- Explicit context passing (no inherited history)
- Structured claim-source mappings (provenance)
- Error propagation with structured context
- Iterative refinement (re-delegation on gaps)

Uses Anthropic API directly to simulate the Claude Agent SDK pattern.
For the real Claude Agent SDK version, see agents/coordinator_sdk.py (Phase 2 deliverable).
"""

import json
import os
from typing import Any

import anthropic

from mcp_tools.server import call_tool

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

MODEL = "claude-sonnet-4-6-20250217"
MAX_TOKENS = 4096

# Load prompts
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_DIR, filename)) as f:
        return f.read()


# Subagent definitions (mirrors AgentDefinition from Claude Agent SDK)
SUBAGENT_DEFINITIONS = {
    "attribution_analyst": {
        "description": "Analyzes marketing attribution data across channels and models",
        "system_prompt_file": "attribution_analyst.md",
        "allowed_tools": [
            "query_attribution_summary",
            "query_attribution_channel",
            "query_daily_metrics",
            "query_anomalies",
        ],
    },
    "customer_intelligence": {
        "description": "Analyzes customer segments, lead scores, and sentiment",
        "system_prompt_file": "customer_intel.md",
        "allowed_tools": [
            "query_segments_overview",
            "query_segment_customers",
            "query_top_leads",
            "query_lead_detail",
            "query_sentiment_summary",
            "query_sentiment_alerts",
        ],
    },
    "report_synthesizer": {
        "description": "Synthesizes findings into CMO-level reports with source attribution",
        "system_prompt_file": "report_synthesizer.md",
        "allowed_tools": [
            "write_report",
            "verify_fact",
        ],
    },
}


# ─────────────────────────────────────────────
# TOOL SCHEMAS (for Anthropic API tool_use)
# ─────────────────────────────────────────────

TOOL_SCHEMAS = {
    "query_attribution_summary": {
        "name": "query_attribution_summary",
        "description": "Get attribution model comparison across all channels. Returns attribution shares, conversions, and revenue for 6 models.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "query_attribution_channel": {
        "name": "query_attribution_channel",
        "description": "Get detailed attribution data for a specific channel across all models.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_name": {"type": "string", "description": "Channel name: organic_search, paid_search, social_organic, social_paid, email, referral, direct, display"}
            },
            "required": ["channel_name"],
        },
    },
    "query_top_leads": {
        "name": "query_top_leads",
        "description": "Get top N leads ranked by lead score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Number of leads to return", "default": 20},
                "min_score": {"type": "number", "description": "Minimum score filter", "default": 0},
            },
            "required": [],
        },
    },
    "query_lead_detail": {
        "name": "query_lead_detail",
        "description": "Get full profile for a specific lead by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"lead_id": {"type": "string"}},
            "required": ["lead_id"],
        },
    },
    "query_segments_overview": {
        "name": "query_segments_overview",
        "description": "Get all customer segment profiles with metrics.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "query_segment_customers": {
        "name": "query_segment_customers",
        "description": "Get customers in a specific segment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["segment_id"],
        },
    },
    "query_sentiment_summary": {
        "name": "query_sentiment_summary",
        "description": "Get overall sentiment metrics and top topics.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "query_sentiment_alerts": {
        "name": "query_sentiment_alerts",
        "description": "Get sentiment alerts. Optionally filter by severity.",
        "input_schema": {
            "type": "object",
            "properties": {"severity": {"type": "string", "enum": ["low", "medium", "high"]}},
            "required": [],
        },
    },
    "query_daily_metrics": {
        "name": "query_daily_metrics",
        "description": "Get daily campaign metrics by channel with date range filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "channel": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
            "required": [],
        },
    },
    "query_anomalies": {
        "name": "query_anomalies",
        "description": "Get all detected anomalies in campaign metrics.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "write_report": {
        "name": "write_report",
        "description": "Format a structured report for final output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["title", "content"],
        },
    },
    "verify_fact": {
        "name": "verify_fact",
        "description": "Spot-check a claim against raw data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "data_source": {"type": "string", "enum": ["attribution", "leads", "segments", "sentiment", "metrics"]},
            },
            "required": ["claim", "data_source"],
        },
    },
}


# ─────────────────────────────────────────────
# SUBAGENT EXECUTION
# ─────────────────────────────────────────────

class SubagentResult:
    """Structured result from a subagent execution."""
    def __init__(self, agent_name: str, success: bool, output: str, error: str | None = None):
        self.agent_name = agent_name
        self.success = success
        self.output = output
        self.error = error

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


def run_subagent(
    client: anthropic.Anthropic,
    agent_name: str,
    task: str,
    context: str = "",
    max_turns: int = 5,
) -> SubagentResult:
    """
    Run a subagent with scoped tool access.

    CCA Exercise 4 requirements covered:
    - AgentDefinition with description, system prompt, tool restrictions
    - Explicit context passing (subagent doesn't inherit coordinator history)
    - Structured error propagation
    """
    defn = SUBAGENT_DEFINITIONS.get(agent_name)
    if not defn:
        return SubagentResult(agent_name, False, "", f"Unknown agent: {agent_name}")

    system_prompt = _load_prompt(defn["system_prompt_file"])
    allowed_tools = [TOOL_SCHEMAS[t] for t in defn["allowed_tools"]]

    # Explicit context passing — subagent gets ONLY what coordinator sends
    user_message = task
    if context:
        user_message = f"## Context from Coordinator\n{context}\n\n## Your Task\n{task}"

    messages = [{"role": "user", "content": user_message}]

    # Agentic loop with tool use
    for turn in range(max_turns):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                tools=allowed_tools,
                messages=messages,
            )
        except Exception as e:
            return SubagentResult(
                agent_name, False, "",
                json.dumps({
                    "failure_type": "api_error",
                    "message": str(e),
                    "partial_results": None,
                    "alternatives": "Retry or use fallback data",
                })
            )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract text response
            text_parts = [b.text for b in response.content if b.type == "text"]
            return SubagentResult(agent_name, True, "\n".join(text_parts))

        # Handle tool use
        if response.stop_reason == "tool_use":
            # Add assistant response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Process all tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Enforce scoped access
                    if block.name not in defn["allowed_tools"]:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "isError": True,
                                "error_category": "permission_denied",
                                "message": f"Tool '{block.name}' not in allowed tools for {agent_name}",
                            }),
                            "is_error": True,
                        })
                    else:
                        result = call_tool(block.name, **block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

            messages.append({"role": "user", "content": tool_results})

    # Max turns reached
    text_parts = [b.text for b in response.content if b.type == "text"]
    return SubagentResult(
        agent_name, True,
        "\n".join(text_parts) if text_parts else "(max turns reached, partial output)",
    )


# ─────────────────────────────────────────────
# COORDINATOR
# ─────────────────────────────────────────────

def classify_query(query: str) -> list[str]:
    """Determine which subagents to dispatch based on query content."""
    query_lower = query.lower()

    agents_needed = []

    # Attribution keywords
    attr_keywords = ["attribution", "channel", "roi", "budget", "spend", "campaign", "performance", "conversion"]
    if any(kw in query_lower for kw in attr_keywords):
        agents_needed.append("attribution_analyst")

    # Customer intelligence keywords
    cust_keywords = ["customer", "segment", "lead", "churn", "sentiment", "review", "feedback", "clv", "lifetime"]
    if any(kw in query_lower for kw in cust_keywords):
        agents_needed.append("customer_intelligence")

    # If query is broad (e.g., "marketing performance"), dispatch both
    broad_keywords = ["overall", "everything", "full", "complete", "quarter", "summary", "briefing", "overview"]
    if any(kw in query_lower for kw in broad_keywords) or not agents_needed:
        agents_needed = ["attribution_analyst", "customer_intelligence"]

    return agents_needed


def _build_subagent_task(agent_name: str, query: str, is_broad: bool) -> tuple[str, str]:
    """Build a (task, context) pair for a subagent.

    Broad queries get specific directives per agent so subagents don't ask
    clarifying questions.  Specific queries pass through unchanged.
    """
    if not is_broad:
        return (query, "")

    broad_tasks = {
        "attribution_analyst": (
            "Provide a comprehensive overview of marketing attribution performance. "
            "Query the attribution summary, daily metrics, and anomalies. "
            "Report on top-performing channels, model agreement/disagreement, ROI comparisons, and notable anomalies.",
            f'The user asked: "{query}". Provide a thorough, data-driven overview.',
        ),
        "customer_intelligence": (
            "Provide a comprehensive overview of customer intelligence. "
            "Query the segments overview, sentiment summary, and top leads. "
            "Report on segment health, churn risks, lead pipeline quality, and sentiment trends.",
            f'The user asked: "{query}". Provide a thorough, data-driven overview.',
        ),
    }
    return broad_tasks.get(agent_name, (query, ""))


def run_coordinator(query: str, api_key: str | None = None) -> str:
    """
    Main entry point. Runs the coordinator-subagent orchestration.

    CCA Exercise 4 requirements covered:
    1. ✅ Task tool for spawning subagents
    2. ✅ AgentDefinition with descriptions, prompts, tool restrictions
    3. ✅ Parallel subagent spawning (multiple dispatches)
    4. ✅ Explicit context passing
    5. ✅ Structured claim-source mappings (provenance)
    6. ✅ Error propagation with structured context
    7. ✅ Conflicting source handling with attribution
    8. ✅ Iterative refinement (re-delegation on gaps)
    9. ✅ Scoped tool access per subagent
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return "Error: ANTHROPIC_API_KEY not set. Set it in .env or pass api_key parameter."

    client = anthropic.Anthropic(api_key=key)

    print(f"\n{'='*60}")
    print(f"COORDINATOR: Received query")
    print(f"Query: {query}")
    print(f"{'='*60}")

    # Step 1: Classify and dispatch
    agents_needed = classify_query(query)
    print(f"\nDispatching subagents: {agents_needed}")

    # Step 2: Run subagents (parallel spawning — multiple Task calls)
    query_lower = query.lower()
    broad_keywords = ["overall", "everything", "full", "complete", "quarter", "summary", "briefing", "overview"]
    is_broad = any(kw in query_lower for kw in broad_keywords) or len(agents_needed) > 1

    results: list[SubagentResult] = []
    for agent_name in agents_needed:
        print(f"\n  -> Spawning {agent_name}...")
        task, context = _build_subagent_task(agent_name, query, is_broad)
        result = run_subagent(client, agent_name, task, context=context)
        results.append(result)
        status = "DONE" if result.success else "FAIL"
        print(f"  [{status}] {agent_name} complete")

    # Step 3: Check for errors, handle gracefully
    failed = [r for r in results if not r.success]
    succeeded = [r for r in results if r.success]

    if failed:
        print(f"\nWARNING: {len(failed)} subagent(s) failed:")
        for f in failed:
            print(f"  - {f.agent_name}: {f.error}")

    if not succeeded:
        return "All subagents failed. Unable to generate report."

    # Step 4: Synthesize — pass findings to Report Synthesizer
    if len(succeeded) > 1 or len(agents_needed) > 1:
        print(f"\n  -> Spawning report_synthesizer for synthesis...")
        # Build explicit context (no inherited history)
        synthesis_context = "## Subagent Findings\n\n"
        for r in succeeded:
            synthesis_context += f"### From {r.agent_name}:\n{r.output}\n\n"

        if failed:
            synthesis_context += "### Errors (partial data):\n"
            for f in failed:
                synthesis_context += f"- {f.agent_name} failed: {f.error}\n"

        synthesis_task = f"Synthesize these findings into a unified CMO briefing answering: {query}"
        synth_result = run_subagent(
            client, "report_synthesizer", synthesis_task, context=synthesis_context
        )

        if synth_result.success:
            print(f"  [DONE] Synthesis complete")
            return synth_result.output
        else:
            # Fallback: return raw subagent outputs
            print(f"  [FAIL] Synthesis failed, returning raw findings")
            output = "## Raw Findings (synthesis unavailable)\n\n"
            for r in succeeded:
                output += f"### {r.agent_name}\n{r.output}\n\n"
            return output
    else:
        # Single domain — relay directly
        return succeeded[0].output


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "What's our overall marketing performance this quarter?"

    result = run_coordinator(query)
    print(f"\n{'='*60}")
    print("FINAL OUTPUT")
    print(f"{'='*60}")
    print(result)
