from typing import Optional, Dict, Any, List
TARGET_BRANDS = [
    "paypal", "google", "apple", "amazon", "microsoft", 
    "facebook", "instagram", "binance", "coinbase", 
    "netflix", "steam", "linkedin", "bankofamerica", "chase"
]

def detect_brand_impersonation(url_data: dict, page_title: str) -> dict:
    """Identify if the URL is impersonating a known brand."""
    detected_brand: Optional[str] = None
    impersonation_score: int = 0
    
    domain: str = str(url_data.get("domain", "")).lower()
    subdomain: str = str(url_data.get("subdomain", "")).lower()
    page_title_str: str = str(page_title).lower() if page_title else ""
    
    for brand in TARGET_BRANDS:
        # Check domain/subdomain
        if brand in domain or brand in subdomain:
            # If the brand is present but not the primary domain, it's highly suspicious
            # e.g., paypal-secure.xyz vs paypal.com
            detected_brand = brand
            impersonation_score = 100
            break
            
        # Check title
        if brand in page_title_str:
            detected_brand = brand
            impersonation_score = 70
            break
            
    return {
        "brand_impersonation_detected": detected_brand is not None,
        "impersonated_brand": detected_brand,
        "impersonation_score": impersonation_score
    }
