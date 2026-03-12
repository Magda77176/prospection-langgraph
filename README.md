# Prospection Pipeline — LangGraph

Multi-channel B2B prospection pipeline built with **LangGraph**. Automatically routes prospects through the best contact channel (email or LinkedIn) based on data availability.

## The Graph

```
scrape → enrich → verify_email
                      │
            ┌─────────┴──────────┐
            ▼                    ▼
     email verified?          invalid
            │                    │
            ▼                    ▼
      draft_email         search_linkedin
            │                    │
            │           ┌───────┴────────┐
            │           ▼                ▼
            │      found?            not found
            │           │                │
            │           ▼                ▼
            │    draft_linkedin     no_channel
            │           │                │
            └─────┬─────┘                │
                  ▼                      │
                send ←───────────────────┘
                  │
                  ▼
             update_crm
                  │
                  ▼
                 END
```

## How It Works

**Input:** `{"name": "Dr. Martin Dupont", "city": "Paris", "sector": "dentiste"}`

**What the graph does:**
1. **Scrape** — Google SERP + Places via Serper.dev → website, phone, address
2. **Enrich** — Mentions légales → SIRET → Societe.com → dirigeant name → email patterns
3. **Verify** — Hunter.io checks email deliverability (score 0-100)
4. **Route** — Score > 80? → email path. Otherwise → LinkedIn fallback
5. **Draft** — LLM writes personalized message referencing their website/city
6. **Send** — Email via SMTP or LinkedIn via browser automation
7. **CRM** — Update Google Sheets with all data

**Example output:**
```
→ scraped: 2 results, website: https://dr-dupont-dentiste.fr
→ enriched: SIRET 823 456 789 00015, dirigeant Martin DUPONT
→ email pattern: dr.dupont@gmail.com
→ hunter verify: score 91 (deliverable)
→ email drafted (personalized)
→ email sent to dr.dupont@gmail.com
→ CRM updated: row 2344, status contacted
```

## Why LangGraph (not ADK)

| Aspect | Why LangGraph fits here |
|--------|------------------------|
| **Routing is deterministic** | Email valid → send email. No LLM needed for routing. |
| **Fallback chains** | Email fails → LinkedIn → no channel. Explicit edges. |
| **State accumulates** | Each node adds to the shared TypedDict state |
| **Batch processing** | No LLM overhead for orchestration = fast + cheap |
| **Visualization** | The graph IS the documentation |

ADK is better when the LLM should *decide* the flow. Here, the data decides.

## Stack

| Layer | Technology |
|-------|-----------|
| Pipeline | LangGraph — `StateGraph` with conditional edges |
| API | FastAPI + Pydantic v2 |
| Search | Serper.dev ($0.001/req) |
| Email verification | Hunter.io |
| Enrichment | Societe.com (SIRET → dirigeant) |
| Message drafting | Gemini / Claude (LLM) |
| Sending | SMTP (email) / Chrome Bridge (LinkedIn) |
| CRM | Google Sheets API |
| Tests | pytest — 17 tests |

## Quick Start

```bash
pip install langgraph fastapi uvicorn pydantic

# Process one prospect
python -c "
from prospection_graph.graph import run_prospect
result = run_prospect('Dr. Dupont', 'Paris', 'dentiste')
print(result['status'], result['channel'])
"

# Run API
python main.py  # :8081

# Run tests
pytest tests/ -v
```

## API

```bash
# Single prospect
curl -X POST http://localhost:8081/prospect \
  -H "Content-Type: application/json" \
  -d '{"name": "Dr. Dupont", "city": "Paris", "sector": "dentiste"}'

# Batch (with daily limit)
curl -X POST http://localhost:8081/batch \
  -H "Content-Type: application/json" \
  -d '{"prospects": [{"name":"Dr. A","city":"Paris"},{"name":"Dr. B","city":"Lyon"}], "max_per_day": 25}'

# Graph structure
curl http://localhost:8081/graph
```

## Production Integration

This pipeline is designed to plug into an existing prospection stack:
- Replace mock tools with live API calls (Serper, Hunter, Google Sheets)
- Connect LinkedIn sending to Chrome Bridge (Mac) or Cloudflare Worker
- Add rate limiting (25 emails/day, 10 LinkedIn/day)
- Add human-in-the-loop for message review before sending

## Author

**Sullivan Magdaleon** — AI & Automation Engineer  
Multi-agent systems in production · LangGraph · Google ADK  
[LinkedIn](https://linkedin.com/in/sullivan-magdaleon-980203130)
