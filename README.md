# 🧠 Unified Marketing Intelligence Platform

A unified marketing intelligence platform that ties together data from 8 specialized marketing analytics projects into a single hub, powered by multi-agent orchestration.

## What This Does

This platform combines outputs from multiple marketing analytics systems:
- **Attribution Analysis** (P6) — Multi-touch attribution across 6 models (Markov chain, Shapley, rule-based)
- **Lead Scoring** (P4) — XGBoost-based lead prioritization with SHAP explainability
- **Customer Segmentation** (P5) — RFM + K-means clustering with CLV prediction
- **NLP Sentiment Analysis** (P8) — DistilBERT sentiment classification with BERTopic clustering
- **Campaign Metrics & Anomaly Detection** (P1) — Daily metrics with z-score anomaly detection
- **Data Pipeline** (P7) — ETL pipeline with FastAPI serving layer

Instead of checking 6 different dashboards, a CMO can ask one question and get a unified answer.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  USER QUERY                       │
│  "What's our marketing performance this quarter?" │
└─────────────────────┬────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────┐
│            COORDINATOR AGENT (Claude)             │
│  - Decomposes query into subtasks                 │
│  - Dispatches subagents in parallel               │
│  - Evaluates synthesis for gaps                   │
│  - Re-delegates if needed                         │
└───────┬──────────────┬──────────────┬────────────┘
        │              │              │
        ▼              ▼              ▼
   ATTRIBUTION    CUSTOMER       REPORT
   ANALYST        INTELLIGENCE   SYNTHESIZER
   (scoped tools) (scoped tools) (scoped tools)
        │              │              │
        ▼              ▼              ▼
┌──────────────────────────────────────────────────┐
│           12 MCP TOOLS → FastAPI (11 endpoints)   │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│           SYNTHETIC DATA (simulating P1-P8)       │
│  5,000 customers · 2,920 daily metrics · 1,200    │
│  leads · 2,000 reviews · 500 attribution paths    │
└──────────────────────────────────────────────────┘
```

## Tech Stack

- **Python 3.12+**
- **FastAPI** — 11 REST endpoints with Pydantic validation, Swagger docs
- **Anthropic API** — Multi-agent orchestration (coordinator + 3 subagents)
- **Streamlit** — 5-tab dashboard (Executive Summary, Attribution, Customers, Sentiment, AI Analyst)
- **Plotly** — Interactive charts (heatmaps, scatter plots, bar charts)
- **Faker + NumPy** — Realistic synthetic data generation
- **pandas + scikit-learn** — Data processing

## Quick Start

```bash
# Clone
git clone https://github.com/mufibra23/unified-marketing-intelligence.git
cd unified-marketing-intelligence

# Setup
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Generate synthetic data
python data/generate_synthetic.py

# Test API (11 endpoints)
uvicorn api.main:app --reload
# Visit http://localhost:8000/docs for Swagger

# Test MCP tools (12 tools)
python -m mcp_tools.server

# Run dashboard
streamlit run streamlit_app/app.py

# Run AI analyst (requires ANTHROPIC_API_KEY in .env)
python agents/coordinator.py "Which channel has the highest ROI?"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/attribution/summary` | GET | All attribution models comparison |
| `/api/v1/attribution/channel/{channel}` | GET | Per-channel attribution detail |
| `/api/v1/leads/top` | GET | Top leads by score |
| `/api/v1/leads/{lead_id}` | GET | Individual lead profile |
| `/api/v1/segments/overview` | GET | All segment profiles |
| `/api/v1/segments/{id}/customers` | GET | Customers in a segment |
| `/api/v1/sentiment/summary` | GET | Overall sentiment metrics |
| `/api/v1/sentiment/alerts` | GET | Negative sentiment spikes |
| `/api/v1/metrics/daily` | GET | Daily campaign metrics |
| `/api/v1/metrics/anomalies` | GET | Detected anomalies |

## Multi-Agent Architecture

The coordinator agent implements the **hub-and-spoke pattern**:

1. **Query Classification** — Determines which domains the query touches
2. **Parallel Dispatch** — Spawns multiple subagents simultaneously
3. **Scoped Tool Access** — Each subagent only accesses its relevant tools
4. **Provenance Tracking** — Every claim maps to a specific data source
5. **Conflict Resolution** — When models disagree, both values are reported with attribution
6. **Iterative Refinement** — Coordinator can re-delegate if synthesis has gaps

## Project Structure

```
unified-marketing-intelligence/
├── api/
│   ├── main.py              # FastAPI app (11 endpoints)
│   ├── data_loader.py       # Data loading with caching
│   └── models/schemas.py    # Pydantic response schemas
├── agents/
│   ├── coordinator.py       # Multi-agent coordinator
│   └── prompts/             # Externalized system prompts
│       ├── coordinator.md
│       ├── attribution_analyst.md
│       ├── customer_intel.md
│       └── report_synthesizer.md
├── mcp_tools/
│   └── server.py            # 12 MCP tools wrapping FastAPI
├── data/
│   ├── generate_synthetic.py # Synthetic data generator
│   └── synthetic/           # Generated CSV/JSON files
├── streamlit_app/
│   └── app.py               # 5-tab dashboard
├── requirements.txt
└── README.md
```

## Cost

- **Synthetic data, FastAPI, Streamlit, MCP tools**: $0 (all open-source)
- **Anthropic API** (AI Analyst tab): ~$5-10 for development/testing
- **Total**: ~$5-10

## Built By

Muhammad Fariz Ibrahim — [GitHub](https://github.com/mufibra23)

Part of a 10-project AI Marketing Analytics portfolio. This is Project 9: the unification layer that ties everything together.
