"""
Pipeline State — TypedDict shared between all nodes.
This is LangGraph's core concept: explicit, typed state that flows through the graph.
"""

from typing import TypedDict, Optional, Literal


class ProspectState(TypedDict, total=False):
    # --- Input ---
    name: str                    # Business name (e.g. "Dr. Martin Dupont")
    city: str                    # Target city
    sector: str                  # "dentiste", "photographe", "artisan"
    campaign: str                # Campaign ID for tracking

    # --- Scraping ---
    search_results: list         # Raw SERP results
    website: Optional[str]       # Extracted website URL
    phone: Optional[str]         # Phone number if found
    address: Optional[str]       # Physical address

    # --- Enrichment ---
    siret: Optional[str]         # SIRET from mentions légales
    dirigeant: Optional[str]     # Owner name from Societe.com
    email: Optional[str]         # Found email
    email_source: Optional[str]  # "mentions_legales", "pattern", "hunter"
    email_score: int             # Hunter.io verification score (0-100)
    email_verified: bool         # Score > 80

    # --- LinkedIn ---
    linkedin_url: Optional[str]  # LinkedIn profile URL
    linkedin_degree: Optional[int]  # 1st, 2nd, 3rd degree connection
    linkedin_action: Optional[str]  # "message", "invitation", "none"

    # --- Action ---
    channel: Optional[str]       # "email", "linkedin_message", "linkedin_invitation", "none"
    message_draft: Optional[str] # Personalized message (written by LLM)
    message_sent: bool           # Was the message actually sent?
    
    # --- CRM ---
    crm_updated: bool            # Updated in Google Sheets
    crm_row: Optional[int]       # Row number in CRM

    # --- Meta ---
    status: str                  # "processing", "contacted", "no_channel", "error"
    error: Optional[str]         # Error message if failed
    retry_count: int             # Number of retries
    steps_log: list              # Log of all steps taken
