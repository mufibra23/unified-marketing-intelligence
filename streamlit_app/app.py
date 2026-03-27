"""
Unified Marketing Intelligence Platform — Streamlit Dashboard
5 tabs: Executive Summary, Attribution, Customer Intelligence, Sentiment, AI Analyst

Run: streamlit run streamlit_app/app.py
"""

import json
import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp_tools.server import call_tool

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Marketing Intelligence Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .stMetric { border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_tool(name: str, **kwargs) -> dict:
    """Call an MCP tool and parse the JSON response."""
    raw = call_tool(name, **kwargs)
    result = json.loads(raw)
    if result.get("success"):
        return result.get("data", result)
    return {}


# ─────────────────────────────────────────────
# TAB 1: EXECUTIVE SUMMARY
# ─────────────────────────────────────────────

def render_executive_summary():
    st.header("📊 Executive Summary")

    # Fetch key data
    sentiment = fetch_tool("query_sentiment_summary")
    segments = fetch_tool("query_segments_overview")
    anomalies_data = fetch_tool("query_anomalies")
    leads = fetch_tool("query_top_leads", n=100)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_sent = sentiment.get("avg_sentiment", 0)
        st.metric("Avg Sentiment", f"{avg_sent:.2f}", "Positive" if avg_sent > 0 else "Negative")

    with col2:
        total_leads = leads.get("total_count", 0)
        avg_score = leads.get("avg_score", 0)
        st.metric("Active Leads", total_leads, f"Avg Score: {avg_score:.1f}")

    with col3:
        n_segments = len(segments) if isinstance(segments, list) else 0
        st.metric("Customer Segments", n_segments)

    with col4:
        n_anomalies = anomalies_data.get("total_anomalies", 0)
        st.metric("Anomalies Detected", n_anomalies, "⚠️" if n_anomalies > 5 else "✅")

    st.divider()

    # Segment health overview
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Segment Health")
        if isinstance(segments, list) and segments:
            seg_df = pd.DataFrame(segments)
            fig = px.bar(
                seg_df,
                x="segment_name",
                y="churn_rate",
                color="churn_rate",
                color_continuous_scale="RdYlGn_r",
                title="Churn Rate by Segment",
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Sentiment Distribution")
        if sentiment:
            fig = go.Figure(data=[go.Pie(
                labels=["Positive", "Neutral", "Negative"],
                values=[
                    sentiment.get("positive_pct", 0),
                    sentiment.get("neutral_pct", 0),
                    sentiment.get("negative_pct", 0),
                ],
                marker_colors=["#2ecc71", "#95a5a6", "#e74c3c"],
                hole=0.4,
            )])
            fig.update_layout(height=350, title="Review Sentiment Split")
            st.plotly_chart(fig, use_container_width=True)

    # Anomaly feed
    st.subheader("⚠️ Recent Anomalies")
    if anomalies_data.get("anomalies"):
        anom_df = pd.DataFrame(anomalies_data["anomalies"][:10])
        st.dataframe(anom_df, use_container_width=True, hide_index=True)
    else:
        st.info("No anomalies detected.")


# ─────────────────────────────────────────────
# TAB 2: ATTRIBUTION INTELLIGENCE
# ─────────────────────────────────────────────

def render_attribution():
    st.header("🎯 Attribution Intelligence")

    attr_data = fetch_tool("query_attribution_summary")

    if not attr_data or "results" not in attr_data:
        st.warning("No attribution data available.")
        return

    df = pd.DataFrame(attr_data["results"])

    # Model comparison heatmap
    st.subheader("Model Comparison: Attribution Share by Channel")
    pivot = df.pivot_table(
        index="channel", columns="model", values="attribution_share", aggfunc="mean"
    )
    fig = px.imshow(
        pivot,
        text_auto=".3f",
        color_continuous_scale="Viridis",
        aspect="auto",
        title="Attribution Share Heatmap (Channels × Models)",
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

    # Per-channel detail
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Average Attribution Share")
        avg_by_channel = df.groupby("channel")["attribution_share"].mean().sort_values(ascending=True)
        fig = px.barh(
            x=avg_by_channel.values,
            y=avg_by_channel.index,
            labels={"x": "Avg Attribution Share", "y": "Channel"},
            title="Channel Ranking (Avg Across Models)",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Model Disagreement")
        std_by_channel = df.groupby("channel")["attribution_share"].std().sort_values(ascending=False)
        fig = px.bar(
            x=std_by_channel.index,
            y=std_by_channel.values,
            labels={"x": "Channel", "y": "Std Dev of Attribution Share"},
            title="Where Models Disagree Most",
            color=std_by_channel.values,
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Budget recommendation
    st.subheader("💰 Budget Reallocation Signals")
    st.info(
        "Channels where **Markov chain** attribution is significantly higher than rule-based models "
        "suggest hidden value — these channels assist conversions even if they're not first/last touch."
    )
    markov = df[df["model"] == "markov_chain"].set_index("channel")["attribution_share"]
    first_click = df[df["model"] == "first_click"].set_index("channel")["attribution_share"]
    diff = (markov - first_click).sort_values(ascending=False)
    diff_df = pd.DataFrame({"channel": diff.index, "markov_vs_first_click_diff": diff.values})
    st.dataframe(diff_df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# TAB 3: CUSTOMER INTELLIGENCE
# ─────────────────────────────────────────────

def render_customer_intelligence():
    st.header("👥 Customer Intelligence")

    segments = fetch_tool("query_segments_overview")
    leads = fetch_tool("query_top_leads", n=20, min_score=50)

    if not segments:
        st.warning("No segment data available.")
        return

    # Segment overview
    st.subheader("Customer Segments")
    seg_df = pd.DataFrame(segments)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.scatter(
            seg_df,
            x="avg_lifetime_value",
            y="churn_rate",
            size="customer_count",
            color="segment_name",
            hover_data=["recommended_action"],
            title="Segment Map: LTV vs Churn",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            seg_df,
            x="segment_name",
            y="customer_count",
            color="avg_sentiment",
            color_continuous_scale="RdYlGn",
            title="Segment Size & Sentiment",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Segment details table
    st.subheader("Segment Profiles")
    display_cols = [
        "segment_name", "customer_count", "avg_lifetime_value",
        "churn_rate", "avg_sentiment", "top_channel", "recommended_action"
    ]
    st.dataframe(seg_df[display_cols], use_container_width=True, hide_index=True)

    # Top leads
    st.divider()
    st.subheader("🔥 Top Leads (Score ≥ 50)")
    if leads and leads.get("leads"):
        leads_df = pd.DataFrame(leads["leads"])
        display_cols = [
            "lead_id", "name", "company", "industry",
            "lead_score", "engagement_score", "conversion_probability", "lead_source"
        ]
        st.dataframe(leads_df[display_cols], use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# TAB 4: SENTIMENT MONITOR
# ─────────────────────────────────────────────

def render_sentiment():
    st.header("💬 Sentiment Monitor")

    sentiment = fetch_tool("query_sentiment_summary")
    alerts_data = fetch_tool("query_sentiment_alerts")

    if not sentiment:
        st.warning("No sentiment data available.")
        return

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Reviews", sentiment.get("total_reviews", 0))
    with col2:
        st.metric("Avg Sentiment", f"{sentiment.get('avg_sentiment', 0):.3f}")
    with col3:
        st.metric("Avg Stars", f"{sentiment.get('avg_star_rating', 0):.1f} ⭐")
    with col4:
        neg_pct = sentiment.get("negative_pct", 0)
        st.metric("Negative %", f"{neg_pct:.1f}%", "⚠️" if neg_pct > 30 else "✅")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Top Positive Topics")
        pos_topics = sentiment.get("top_positive_topics", [])
        for i, topic in enumerate(pos_topics, 1):
            st.write(f"  {i}. ✅ {topic}")

    with col_right:
        st.subheader("Top Negative Topics")
        neg_topics = sentiment.get("top_negative_topics", [])
        for i, topic in enumerate(neg_topics, 1):
            st.write(f"  {i}. ❌ {topic}")

    # Alerts
    st.divider()
    st.subheader("🚨 Sentiment Alerts")
    if alerts_data and alerts_data.get("alerts"):
        alerts_df = pd.DataFrame(alerts_data["alerts"])

        # Color by severity
        severity_filter = st.multiselect(
            "Filter by severity",
            options=["low", "medium", "high"],
            default=["medium", "high"],
        )
        filtered = alerts_df[alerts_df["severity"].isin(severity_filter)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.success("No active sentiment alerts.")


# ─────────────────────────────────────────────
# TAB 5: AI ANALYST (Chat Interface)
# ─────────────────────────────────────────────

def render_ai_analyst():
    st.header("🤖 AI Marketing Analyst")
    st.caption(
        "Ask questions about your marketing performance. "
        "The AI coordinator dispatches specialized subagents to gather data and synthesize insights."
    )

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask about marketing performance..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY")
            if not api_key:
                st.error("ANTHROPIC_API_KEY not set. Add it to your .env file or Streamlit secrets.")
                return

            with st.spinner("Dispatching subagents..."):
                from agents.coordinator import run_coordinator

                try:
                    response = run_coordinator(prompt, api_key=api_key)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Agent error: {e}")

    # Example queries
    if not st.session_state.messages:
        st.divider()
        st.subheader("Try these queries:")
        example_queries = [
            "What's our overall marketing performance this quarter?",
            "Which channel has the highest ROI?",
            "Show me our highest-risk customer segments",
            "Are there any sentiment alerts I should know about?",
            "Deep dive on our lead pipeline health",
        ]
        for q in example_queries:
            st.markdown(f"- *{q}*")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    st.title("🧠 Unified Marketing Intelligence Platform")
    st.caption("P9 — Tying together P1-P8 with multi-agent orchestration")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Executive Summary",
        "🎯 Attribution",
        "👥 Customers",
        "💬 Sentiment",
        "🤖 AI Analyst",
    ])

    with tab1:
        render_executive_summary()

    with tab2:
        render_attribution()

    with tab3:
        render_customer_intelligence()

    with tab4:
        render_sentiment()

    with tab5:
        render_ai_analyst()


if __name__ == "__main__":
    main()
