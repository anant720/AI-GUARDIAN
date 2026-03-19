from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any, cast

def analyze_scripts(html_content: str) -> dict:
    """Analyze scripts on the page for suspicious patterns."""
    if not html_content:
        return {"suspicious_scripts_detected": False}
        
    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all("script")
    
    obfuscation_patterns = [
        r"eval\(", r"atob\(", r"String\.fromCharCode", r"unescale\("
    ]
    
    harvesting_patterns = [
        r"\.submit\(", r"XMLHttpRequest", r"fetch\(", r"\.ajax\("
    ]
    
    suspicious_count: int = 0
    obfuscated_count: int = 0
    external_scripts: list[str] = []
    
    for script in scripts:
        src = script.get("src")
        if src:
            external_scripts.append(src)
            continue
            
        content = script.string or ""
        
        # Check for obfuscation
        if any(re.search(p, content) for p in obfuscation_patterns):
            obfuscated_count = int(obfuscated_count + 1)
            suspicious_count = int(suspicious_count + 1)
            
        # Check for harvesting
        if any(re.search(p, content) for p in harvesting_patterns):
            suspicious_count = int(suspicious_count + 1)
            
    display_scripts = cast(List[str], external_scripts)[:5]
    
    return {
        "scripts_count": int(len(scripts)),
        "external_scripts_count": int(len(external_scripts)),
        "obfuscated_scripts_count": int(obfuscated_count),
        "suspicious_scripts_detected": suspicious_count > 0,
        "external_scripts": [str(s) for s in display_scripts]
    }
