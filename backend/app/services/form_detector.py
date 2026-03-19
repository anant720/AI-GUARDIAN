from bs4 import BeautifulSoup
from typing import Dict, Any, cast, List

def detect_credential_forms(html_content: str) -> dict:
    """Detect presence of credential harvesting forms."""
    if not html_content:
        return {"credential_form_detected": False}
        
    soup = BeautifulSoup(html_content, 'html.parser')
    forms = soup.find_all("form")
    
    suspicious_forms: int = 0
    input_fields_count: int = 0
    password_fields_count: int = 0
    
    for form in forms:
        inputs: List[Any] = cast(List[Any], form.find_all("input"))
        input_fields_count = int(input_fields_count + len(inputs))
        
        has_password = False
        has_identifier = False # email, tel, text for username
        
        for inp in inputs:
            type_attr = inp.get("type", "").lower()
            name_attr = inp.get("name", "").lower()
            
            if type_attr == "password":
                password_fields_count = int(password_fields_count + 1)
                has_password = True
            if type_attr in ["email", "tel"] or any(kw in name_attr for kw in ["user", "login", "email", "phone"]):
                has_identifier = True
                
        if has_password:
            suspicious_forms = int(suspicious_forms + 1)
            
    return {
        "credential_form_detected": suspicious_forms > 0,
        "input_fields_count": input_fields_count,
        "password_fields_count": password_fields_count,
        "suspicious_forms_count": suspicious_forms
    }
