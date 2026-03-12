"""
Tools — External API integrations.
In production, these call Serper.dev, Hunter.io, Societe.com, Google Sheets.
Mock responses for demo/testing.
"""

import re
from typing import Optional


def serper_search(query: str) -> dict:
    """Search Google via Serper.dev API ($0.001/req).
    
    Production: POST https://google.serper.dev/search
    """
    # Mock: simulate realistic SERP results
    return {
        "status": "success",
        "results": [
            {
                "title": f"Cabinet Dentaire - {query}",
                "link": "https://dr-dupont-dentiste.fr",
                "snippet": "Dr. Martin Dupont, chirurgien-dentiste à Paris 16e. Implants, orthodontie, soins conservateurs.",
            },
            {
                "title": f"Dr Dupont - Doctolib",
                "link": "https://www.doctolib.fr/dentiste/paris/martin-dupont",
                "snippet": "Prenez rendez-vous avec Dr Martin Dupont, dentiste à Paris.",
            },
        ],
    }


def serper_places(query: str, city: str) -> dict:
    """Search Google Places via Serper.dev ($0.001/req).
    
    Production: POST https://google.serper.dev/places
    """
    return {
        "status": "success",
        "places": [
            {
                "title": "Cabinet Dentaire Dr Dupont",
                "address": "45 Rue de la Pompe, 75016 Paris",
                "phone": "01 45 67 89 10",
                "website": "https://dr-dupont-dentiste.fr",
                "rating": 4.7,
                "reviews": 89,
            }
        ],
    }


def scrape_website(url: str) -> dict:
    """Fetch and extract key info from a website.
    
    Production: web_fetch or tools/reader-scraper.js
    """
    return {
        "status": "success",
        "title": "Cabinet Dentaire Dr Dupont - Paris 16e",
        "mentions_legales": {
            "siret": "823 456 789 00015",
            "email": None,  # Not always available
            "phone": "01 45 67 89 10",
        },
        "pages_count": 8,
        "has_blog": False,
        "technologies": ["WordPress"],
    }


def societe_com_lookup(siret: str) -> dict:
    """Look up company info from SIRET via Societe.com.
    
    Production: web_fetch https://www.societe.com/societe/{siret}
    """
    return {
        "status": "success",
        "company_name": "SELARL Dr Dupont Martin",
        "dirigeant": "Martin DUPONT",
        "creation_date": "2015-03-12",
        "naf_code": "86.23Z",
        "naf_label": "Pratique dentaire",
        "city": "Paris",
    }


def generate_email_patterns(name: str, domain: Optional[str] = None) -> list:
    """Generate likely email patterns for a medical professional.
    
    Based on validated patterns (95% hit rate for dr.nom@gmail.com).
    """
    # Clean name
    parts = name.lower().replace("dr.", "").replace("dr ", "").strip().split()
    if len(parts) < 2:
        return []
    
    prenom, nom = parts[0], parts[-1]
    
    patterns = [
        f"dr.{nom}@gmail.com",           # 95% hit rate
        f"dr.{prenom}.{nom}@gmail.com",
        f"dr.{nom}1@gmail.com",
        f"cabinet.{nom}@gmail.com",
        f"contact@dr-{nom}.fr",
    ]
    
    if domain:
        patterns.append(f"contact@{domain}")
        patterns.append(f"dr.{nom}@{domain}")
    
    return patterns


def hunter_verify(email: str) -> dict:
    """Verify email deliverability via Hunter.io.
    
    Production: GET https://api.hunter.io/v2/email-verifier?email={email}
    """
    # Mock: dr.nom@gmail.com patterns score high
    score = 91 if email.startswith("dr.") else 45
    return {
        "status": "success",
        "email": email,
        "score": score,
        "result": "deliverable" if score > 80 else "risky",
        "sources": 2 if score > 80 else 0,
    }


def search_linkedin(name: str, title: str, city: str) -> dict:
    """Search for a LinkedIn profile.
    
    Production: Google search "site:linkedin.com {name} {title} {city}"
    """
    return {
        "status": "success",
        "found": True,
        "url": f"https://www.linkedin.com/in/martin-dupont-dentiste/",
        "degree": 2,  # 2nd degree connection
        "headline": f"Chirurgien-Dentiste | {city}",
    }


def send_email(to: str, subject: str, html_body: str) -> dict:
    """Send personalized email via SMTP.
    
    Production: node tools/send-email.js
    """
    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "message_id": "msg_20260312_001",
    }


def update_google_sheet(row_data: dict) -> dict:
    """Update CRM Google Sheet with prospect data.
    
    Production: Google Sheets API
    """
    return {
        "status": "updated",
        "sheet": "CRM Prospects",
        "row": 2344,
    }
