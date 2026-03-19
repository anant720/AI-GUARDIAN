import dns.resolver
from app.logger import logger
from typing import Dict, Any, List

def get_dns_intelligence(domain: str) -> dict:
    """Collect DNS records for a domain."""
    results = {
        "A": [],
        "MX": [],
        "TXT": [],
        "NS": []
    }
    
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2.0
        resolver.lifetime = 2.0
        
        # A records
        try:
            a_records = resolver.resolve(domain, 'A')
            results["A"] = [str(rdata) for rdata in a_records]
        except Exception: pass
            
        # MX records
        try:
            mx_records = resolver.resolve(domain, 'MX')
            results["MX"] = [str(rdata.exchange) for rdata in mx_records]
        except Exception: pass
            
        # TXT records
        try:
            txt_records = resolver.resolve(domain, 'TXT')
            results["TXT"] = [str(rdata) for rdata in txt_records]
        except Exception: pass
            
        # NS records
        try:
            ns_records = resolver.resolve(domain, 'NS')
            results["NS"] = [str(rdata) for rdata in ns_records]
        except Exception: pass
            
    except Exception as e:
        logger.error(f"DNS lookup failed for {domain}: {e}")
        
    return results
