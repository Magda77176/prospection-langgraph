"""
Prospection Pipeline API — FastAPI + LangGraph
REST API for the B2B prospection multi-channel pipeline.
"""

import os
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional
from prospection_graph.graph import run_prospect, run_batch, build_graph

app = FastAPI(
    title="Prospection Pipeline API",
    description="Multi-channel B2B prospection pipeline built with LangGraph. Routes prospects through email or LinkedIn based on data availability.",
    version="1.0.0",
)


class ProspectRequest(BaseModel):
    name: str = Field(..., description="Business/professional name")
    city: str = Field(..., description="Target city")
    sector: str = Field("dentiste", description="Sector: dentiste, photographe, artisan")
    campaign: str = Field("api", description="Campaign ID for tracking")


class BatchRequest(BaseModel):
    prospects: list[ProspectRequest]
    max_per_day: int = Field(25, description="Max emails per day")


@app.post("/prospect")
async def process_prospect(req: ProspectRequest):
    """Process a single prospect through the pipeline."""
    result = run_prospect(
        name=req.name,
        city=req.city,
        sector=req.sector,
        campaign=req.campaign,
    )
    return {
        "name": result["name"],
        "status": result["status"],
        "channel": result.get("channel"),
        "message_sent": result.get("message_sent"),
        "steps": result.get("steps_log", []),
    }


@app.post("/batch")
async def process_batch(req: BatchRequest):
    """Process multiple prospects with daily limits."""
    prospects = [p.model_dump() for p in req.prospects]
    results = run_batch(prospects, max_per_day=req.max_per_day)
    
    summary = {
        "total": len(results),
        "contacted": sum(1 for r in results if r.get("message_sent")),
        "email": sum(1 for r in results if r.get("channel") == "email"),
        "linkedin": sum(1 for r in results if r.get("channel", "").startswith("linkedin")),
        "no_channel": sum(1 for r in results if r.get("status") == "no_channel"),
    }
    
    return {"summary": summary, "results": [
        {"name": r["name"], "status": r["status"], "channel": r.get("channel")}
        for r in results
    ]}


@app.get("/graph")
async def get_graph_structure():
    """Return the graph structure (nodes and edges)."""
    graph = build_graph()
    compiled = graph.compile()
    return {
        "description": "Prospection pipeline — LangGraph StateGraph",
        "flow": "scrape → enrich → verify_email → [email | linkedin | no_channel] → send → CRM",
        "nodes": list(compiled.get_graph().nodes.keys()),
        "routing": {
            "after_verify_email": "email_verified → draft_email | else → search_linkedin",
            "after_linkedin": "linkedin_found → draft_linkedin | else → no_channel",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "framework": "LangGraph", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "name": "Prospection Pipeline",
        "framework": "LangGraph (StateGraph)",
        "flow": "scrape → enrich → verify → [email OR linkedin] → send → CRM",
        "endpoints": {
            "POST /prospect": "Process single prospect",
            "POST /batch": "Process batch with daily limits",
            "GET /graph": "Graph structure and routing logic",
        },
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
