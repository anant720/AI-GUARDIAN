from app.utils.url_normalizer import is_valid_url, expand_url, normalize_url
from app.utils.url_parser import parse_url_structure
from app.services.domain_intelligence import get_domain_intelligence
from app.services.dns_analyzer import get_dns_intelligence
from app.services.ssl_checker import get_ssl_details
from app.services.redirect_detector import track_redirect_chain
from app.services.webpage_scraper import fetch_webpage_content
from app.services.form_detector import detect_credential_forms
from app.services.brand_detector import detect_brand_impersonation
from app.services.keyword_detector import analyze_keywords
from app.services.script_analyzer import analyze_scripts
from app.services.risk_engine import calculate_risk_score
from app.logger import logger
import asyncio

async def build_intelligence_report(raw_url: str) -> dict:
    """Orchestrate all analyzers to produce a final report."""
    if not is_valid_url(raw_url):
        return {"error": "Invalid URL or protocol not allowed"}
        
    # 1. Normalization & Expansion
    redirect_data = await track_redirect_chain(raw_url)
    final_url = redirect_data["final_url"]
    normalized_url = normalize_url(final_url)
    
    # 2. Structural Analysis
    structural_data = parse_url_structure(normalized_url)
    domain = structural_data.get("domain")
    tld = structural_data.get("tld")
    hostname = f"{domain}.{tld}" if domain and tld else ""
    
    # 3. Parallel Analysis (Step 15 optimization)
    # We run background and content fetch in parallel
    tasks = [fetch_webpage_content(final_url)]
    if hostname:
        tasks.extend([
            asyncio.to_thread(get_domain_intelligence, hostname),
            asyncio.to_thread(get_dns_intelligence, hostname),
            asyncio.to_thread(get_ssl_details, hostname)
        ])
    else:
        # Pad with empty results
        async def empty_dict(): return {}
        tasks.extend([empty_dict(), empty_dict(), empty_dict()])
    
    try:
        # Step 15 optimization: Parallel analysis with strict 3.0s total timeout
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=3.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"URL analysis tasks timed out for {final_url} (limit: 3.0s)")
        # Results will be empty or partial; gather what we can or use defaults
        # For simplicity in this orchestrator, we'll pad the results list to prevent index errors
        results = [{}] * len(tasks)
    except Exception as e:
        logger.error(f"Unexpected error in parallel URL analysis: {e}")
        results = [{}] * len(tasks)
    
    # Unpack results with defaults
    page_content = results[0] if len(results) > 0 else {}
    domain_intel = results[1] if len(results) > 1 else {}
    dns_intel = results[2] if len(results) > 2 else {}
    ssl_intel = results[3] if len(results) > 3 else {}
    
    # 4. Content-based Analysis
    html = page_content.get("html_content", "")
    title = page_content.get("title", "")
    
    form_intel = detect_credential_forms(html)
    brand_intel = detect_brand_impersonation(structural_data, title)
    keyword_intel = analyze_keywords(normalized_url, title, html)
    script_intel = analyze_scripts(html)
    
    # 5. Scoring
    signals = {
        "url_structural": structural_data,
        "domain_intel": domain_intel,
        "dns_intel": dns_intel,
        "ssl_intel": ssl_intel,
        "redirect_intel": redirect_data,
        "page_intel": page_content,
        "form_intel": form_intel,
        "brand_intel": brand_intel,
        "keyword_intel": keyword_intel,
        "script_intel": script_intel
    }
    
    risk_score = calculate_risk_score(signals)
    
    return {
        "url": raw_url,
        "normalized_url": normalized_url,
        "final_url": final_url,
        "risk_score": risk_score,
        "signals": {
            "domain_age_days": domain_intel.get("domain_age_days") if isinstance(domain_intel, dict) else None,
            "suspicious_keywords": keyword_intel.get("found_keywords", []),
            "ssl_valid": ssl_intel.get("ssl_valid", False) if isinstance(ssl_intel, dict) else False,
            "brand_impersonation": brand_intel.get("impersonated_brand"),
            "redirect_count": redirect_data.get("redirect_count", 0),
            "credential_form_detected": form_intel.get("credential_form_detected", False)
        },
        "detailed_report": signals # Include all details for reasoning engine later
    }
