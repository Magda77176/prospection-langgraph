"""
Graph Nodes — Each function is a step in the prospection pipeline.
LangGraph calls them in order defined by the graph edges.
"""

from prospection_graph.state import ProspectState
from prospection_graph import tools


def scrape(state: ProspectState) -> ProspectState:
    """Node 1: Search Google for the prospect."""
    query = f"{state['sector']} {state['name']} {state['city']}"
    
    # Search SERP
    serp = tools.serper_search(query)
    state["search_results"] = serp["results"]
    
    # Search Places for structured data
    places = tools.serper_places(state["name"], state["city"])
    if places["places"]:
        place = places["places"][0]
        state["website"] = place.get("website")
        state["phone"] = place.get("phone")
        state["address"] = place.get("address")
    
    state["steps_log"] = state.get("steps_log", [])
    state["steps_log"].append(f"scraped: {len(serp['results'])} results, website: {state.get('website', 'none')}")
    return state


def enrich(state: ProspectState) -> ProspectState:
    """Node 2: Enrich with SIRET, dirigeant, email patterns."""
    steps = state.get("steps_log", [])
    
    # Scrape website for mentions légales
    if state.get("website"):
        site_data = tools.scrape_website(state["website"])
        if site_data.get("mentions_legales", {}).get("siret"):
            state["siret"] = site_data["mentions_legales"]["siret"]
    
    # SIRET → Societe.com → dirigeant name
    if state.get("siret"):
        societe = tools.societe_com_lookup(state["siret"])
        state["dirigeant"] = societe.get("dirigeant")
        steps.append(f"enriched: SIRET {state['siret']}, dirigeant {state.get('dirigeant')}")
    
    # Generate email patterns from name
    target_name = state.get("dirigeant") or state["name"]
    domain = state.get("website", "").replace("https://", "").replace("http://", "").split("/")[0] if state.get("website") else None
    patterns = tools.generate_email_patterns(target_name, domain)
    
    if patterns:
        # Try first pattern (dr.nom@gmail.com = 95% hit rate)
        state["email"] = patterns[0]
        state["email_source"] = "pattern"
        steps.append(f"email pattern generated: {state['email']}")
    
    state["steps_log"] = steps
    return state


def verify_email(state: ProspectState) -> ProspectState:
    """Node 3: Verify email via Hunter.io."""
    steps = state.get("steps_log", [])
    
    if not state.get("email"):
        state["email_verified"] = False
        state["email_score"] = 0
        steps.append("no email to verify")
        state["steps_log"] = steps
        return state
    
    result = tools.hunter_verify(state["email"])
    state["email_score"] = result["score"]
    state["email_verified"] = result["score"] > 80
    steps.append(f"hunter verify: {state['email']} → score {result['score']} ({result['result']})")
    state["steps_log"] = steps
    return state


def search_linkedin(state: ProspectState) -> ProspectState:
    """Node 4 (fallback): Search LinkedIn profile."""
    steps = state.get("steps_log", [])
    
    target_name = state.get("dirigeant") or state["name"]
    result = tools.search_linkedin(target_name, state["sector"], state["city"])
    
    if result["found"]:
        state["linkedin_url"] = result["url"]
        state["linkedin_degree"] = result["degree"]
        steps.append(f"linkedin found: {result['url']} ({result['degree']}° degré)")
    else:
        steps.append("linkedin: not found")
    
    state["steps_log"] = steps
    return state


def draft_email(state: ProspectState) -> ProspectState:
    """Node 5a: Draft personalized email (LLM-powered)."""
    steps = state.get("steps_log", [])
    
    # In production: call Gemini/Claude to write personalized email
    # referencing their website, city, specialty
    name = state.get("dirigeant") or state["name"]
    city = state["city"]
    website = state.get("website", "votre cabinet")
    
    state["message_draft"] = f"""Bonjour Dr {name.split()[-1]},

J'ai pris le temps de consulter {website} et j'ai remarqué plusieurs axes d'amélioration pour votre visibilité en ligne à {city}.

Votre cabinet a d'excellents avis patients, mais votre site ne ressort pas dans les premières positions Google pour les recherches clés comme "dentiste {city}" ou "implant dentaire {city}".

Seriez-vous disponible pour un échange de 15 minutes cette semaine ?

Sullivan Magdaleon
Infinity Medical — Acquisition digitale pour professionnels de santé"""
    
    state["channel"] = "email"
    steps.append("email drafted (personalized)")
    state["steps_log"] = steps
    return state


def draft_linkedin_message(state: ProspectState) -> ProspectState:
    """Node 5b: Draft LinkedIn message."""
    steps = state.get("steps_log", [])
    
    name = state.get("dirigeant") or state["name"]
    
    if state.get("linkedin_degree") == 1:
        state["message_draft"] = f"""Bonjour Dr {name.split()[-1]},

J'ai vu votre profil et votre cabinet à {state['city']}. Nous aidons les chirurgiens-dentistes à doubler leur visibilité Google locale.

Seriez-vous ouvert à un rapide échange ?

Sullivan"""
        state["channel"] = "linkedin_message"
        state["linkedin_action"] = "message"
        steps.append("linkedin message drafted (1st degree)")
    else:
        state["message_draft"] = f"""Dr {name.split()[-1]}, votre expertise en dentisterie à {state['city']} m'intéresse. J'accompagne des confrères sur leur acquisition digitale. Ravi d'échanger !"""
        state["channel"] = "linkedin_invitation"
        state["linkedin_action"] = "invitation"
        steps.append(f"linkedin invitation drafted ({state.get('linkedin_degree', '?')}° degree)")
    
    state["steps_log"] = steps
    return state


def send_message(state: ProspectState) -> ProspectState:
    """Node 6: Send the message via the chosen channel."""
    steps = state.get("steps_log", [])
    
    if state["channel"] == "email":
        result = tools.send_email(
            to=state["email"],
            subject=f"Visibilité Google de votre cabinet à {state['city']}",
            html_body=state["message_draft"],
        )
        state["message_sent"] = result["status"] == "sent"
        steps.append(f"email sent to {state['email']}")
    
    elif state["channel"] in ("linkedin_message", "linkedin_invitation"):
        # In production: browser automation via Chrome Bridge
        state["message_sent"] = True
        steps.append(f"linkedin {state['linkedin_action']} sent to {state.get('linkedin_url')}")
    
    else:
        state["message_sent"] = False
        steps.append("no channel available — skipped")
    
    state["steps_log"] = steps
    return state


def update_crm(state: ProspectState) -> ProspectState:
    """Node 7: Update CRM with all collected data."""
    steps = state.get("steps_log", [])
    
    result = tools.update_google_sheet({
        "name": state["name"],
        "city": state["city"],
        "website": state.get("website"),
        "email": state.get("email"),
        "phone": state.get("phone"),
        "linkedin": state.get("linkedin_url"),
        "channel": state.get("channel"),
        "status": "contacted" if state.get("message_sent") else "no_channel",
    })
    
    state["crm_updated"] = True
    state["crm_row"] = result.get("row")
    state["status"] = "contacted" if state.get("message_sent") else "no_channel"
    steps.append(f"CRM updated: row {result.get('row')}, status {state['status']}")
    state["steps_log"] = steps
    return state


def mark_no_channel(state: ProspectState) -> ProspectState:
    """Dead end: no email, no LinkedIn → log and move on."""
    steps = state.get("steps_log", [])
    state["channel"] = "none"
    state["status"] = "no_channel"
    steps.append("no contact channel found — marked for manual review")
    state["steps_log"] = steps
    return state
