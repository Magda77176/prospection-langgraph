"""
Graph Definition — The prospection pipeline as a LangGraph StateGraph.

This is where the magic happens: conditional routing based on data,
not LLM decisions. The graph decides the path, LLM writes the messages.

Flow:
    scrape → enrich → verify_email
                         ├─ email valid → draft_email → send → CRM
                         └─ email invalid → search_linkedin
                                              ├─ found → draft_linkedin → send → CRM
                                              └─ not found → mark_no_channel → CRM
"""

from langgraph.graph import StateGraph, END
from prospection_graph.state import ProspectState
from prospection_graph import nodes


# ============================================================
# ROUTING FUNCTIONS — Deterministic, no LLM needed
# ============================================================

def route_after_email_verify(state: ProspectState) -> str:
    """After email verification: valid → draft email, invalid → try LinkedIn."""
    if state.get("email_verified"):
        return "draft_email"
    return "search_linkedin"


def route_after_linkedin(state: ProspectState) -> str:
    """After LinkedIn search: found → draft message, not found → no channel."""
    if state.get("linkedin_url"):
        return "draft_linkedin"
    return "no_channel"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph() -> StateGraph:
    """Construct the prospection pipeline graph."""
    
    graph = StateGraph(ProspectState)
    
    # --- Add nodes ---
    graph.add_node("scrape", nodes.scrape)
    graph.add_node("enrich", nodes.enrich)
    graph.add_node("verify_email", nodes.verify_email)
    graph.add_node("search_linkedin", nodes.search_linkedin)
    graph.add_node("draft_email", nodes.draft_email)
    graph.add_node("draft_linkedin", nodes.draft_linkedin_message)
    graph.add_node("send", nodes.send_message)
    graph.add_node("update_crm", nodes.update_crm)
    graph.add_node("no_channel", nodes.mark_no_channel)
    
    # --- Define edges (the flow) ---
    
    # Linear start: scrape → enrich → verify email
    graph.set_entry_point("scrape")
    graph.add_edge("scrape", "enrich")
    graph.add_edge("enrich", "verify_email")
    
    # Branch 1: email valid? → draft email OR try LinkedIn
    graph.add_conditional_edges(
        "verify_email",
        route_after_email_verify,
        {
            "draft_email": "draft_email",
            "search_linkedin": "search_linkedin",
        },
    )
    
    # Branch 2: LinkedIn found? → draft message OR no channel
    graph.add_conditional_edges(
        "search_linkedin",
        route_after_linkedin,
        {
            "draft_linkedin": "draft_linkedin",
            "no_channel": "no_channel",
        },
    )
    
    # All drafts → send → CRM → END
    graph.add_edge("draft_email", "send")
    graph.add_edge("draft_linkedin", "send")
    graph.add_edge("send", "update_crm")
    graph.add_edge("no_channel", "update_crm")
    graph.add_edge("update_crm", END)
    
    return graph


# ============================================================
# RUN — Process a single prospect
# ============================================================

def run_prospect(name: str, city: str, sector: str = "dentiste", campaign: str = "default") -> ProspectState:
    """Run the full pipeline for one prospect."""
    
    graph = build_graph()
    app = graph.compile()
    
    initial_state: ProspectState = {
        "name": name,
        "city": city,
        "sector": sector,
        "campaign": campaign,
        "retry_count": 0,
        "steps_log": [],
        "message_sent": False,
        "crm_updated": False,
        "email_verified": False,
        "email_score": 0,
    }
    
    result = app.invoke(initial_state)
    return result


# ============================================================
# BATCH — Process multiple prospects
# ============================================================

def run_batch(prospects: list[dict], max_per_day: int = 25) -> list[ProspectState]:
    """Process a batch of prospects with daily limits.
    
    Args:
        prospects: List of {"name": ..., "city": ..., "sector": ...}
        max_per_day: Maximum emails per day (default 25)
    
    Returns:
        List of completed ProspectState results.
    """
    results = []
    emails_sent = 0
    
    for prospect in prospects:
        if emails_sent >= max_per_day:
            break
        
        result = run_prospect(
            name=prospect["name"],
            city=prospect["city"],
            sector=prospect.get("sector", "dentiste"),
            campaign=prospect.get("campaign", "batch"),
        )
        
        if result.get("channel") == "email" and result.get("message_sent"):
            emails_sent += 1
        
        results.append(result)
    
    return results
