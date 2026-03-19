import whois
from datetime import datetime
from app.logger import logger
from typing import Dict, Any, Optional

def get_domain_intelligence(domain: str) -> dict:
    """Gather domain metadata using WHOIS with strict 2.0s timeout."""
    try:
        import socket
        socket.setdefaulttimeout(2.0)
        w = whois.whois(domain)
        
        # Registration dates
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
            
        domain_age_days = None
        if isinstance(creation_date, datetime):
            domain_age_days = (datetime.now() - creation_date).days
            
        return {
            "registrar": w.registrar,
            "registrar_country": w.country,
            "creation_date": creation_date.isoformat() if isinstance(creation_date, datetime) else str(creation_date),
            "domain_age_days": domain_age_days,
            "name_servers": w.name_servers,
            "emails": w.emails,
            "status": w.status
        }
    except Exception as e:
        logger.error(f"Error getting WHOIS for {domain}: {e}")
        return {
            "error": "WHOIS lookup failed",
            "domain_age_days": None
        }
