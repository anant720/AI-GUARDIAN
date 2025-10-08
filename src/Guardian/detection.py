import re
import os
import logging
import requests
import joblib
from urllib.parse import urlparse
from . import rules
from . import utils
import socket, ipaddress
import ssl
from datetime import datetime
from .errors import ModelLoadError
import config
import codecs

LEVEL_SAFE = "Safe"
LEVEL_SUSPICIOUS = "Suspicious"
LEVEL_DANGEROUS = "Dangerous"

VECTORIZER_PATH = config.MODEL_CONFIG['VECTORIZER_PATH']
MODEL_PATH = config.MODEL_CONFIG['MODEL_PATH']

ML_MODEL = None
VECTORIZER = None

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
        ML_MODEL = joblib.load(MODEL_PATH)
        VECTORIZER = joblib.load(VECTORIZER_PATH)
        logging.info("Successfully loaded ML model and vectorizer.")
    else:
        logging.warning("ML model or vectorizer not found. Detection will proceed with rule-based analysis only.")
except Exception as e:
    logging.error(f"Error loading ML model: {e}. Detection will proceed without ML analysis.")
    ML_MODEL, VECTORIZER = None, None

MALICIOUS_DOMAINS_PATH = os.path.join(os.path.dirname(__file__), "model", "malicious_domains.txt")

def decode_punycode(domain):
    """Decode punycode parts in a domain."""
    parts = domain.split('.')
    decoded_parts = []
    for part in parts:
        if part.startswith('xn--'):
            try:
                decoded = codecs.decode(part[4:], 'punycode')
                decoded_parts.append(decoded)
            except:
                decoded_parts.append(part)
        else:
            decoded_parts.append(part)
    return '.'.join(decoded_parts)

def edit_distance(s1, s2):
    """Calculate the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def detect_typosquatting(domain, brand_domains):
    """
    Enhanced typosquatting detection with multiple techniques.
    Returns (risk_score, reason) tuple.
    """
    domain_lower = domain.lower()
    risk_score = 0
    reasons = []
    
    for brand_domain in brand_domains:
        brand = brand_domain.split('.')[0].lower()
        
        # 1. Direct character substitution detection
        char_substitutions = {
            '0': 'o', '1': 'i', '1': 'l', '3': 'e', '4': 'a', 
            '5': 's', '7': 't', '8': 'b', '9': 'g', '6': 'g',
            '2': 'z', '5': 's', '8': 'b'
        }
        
        # Check for number-to-letter substitutions
        normalized_domain = domain_lower
        for num, letter in char_substitutions.items():
            normalized_domain = normalized_domain.replace(num, letter)
        
        if brand in normalized_domain and brand not in domain_lower:
            risk_score += 12
            reasons.append(f"Domain '{domain}' uses number substitution to impersonate '{brand}'")
            continue
            
        # 2. Common typosquatting patterns
        typosquatting_patterns = [
            (f"{brand}0", f"{brand} with 0 instead of o"),
            (f"{brand}1", f"{brand} with 1 instead of i"),
            (f"{brand}3", f"{brand} with 3 instead of e"),
            (f"{brand}4", f"{brand} with 4 instead of a"),
            (f"{brand}5", f"{brand} with 5 instead of s"),
            (f"{brand}7", f"{brand} with 7 instead of t"),
            (f"{brand}8", f"{brand} with 8 instead of b"),
            (f"{brand}9", f"{brand} with 9 instead of g"),
            (f"0{brand}", f"0 instead of o in {brand}"),
            (f"1{brand}", f"1 instead of i in {brand}"),
            (f"3{brand}", f"3 instead of e in {brand}"),
            (f"4{brand}", f"4 instead of a in {brand}"),
            (f"5{brand}", f"5 instead of s in {brand}"),
            (f"7{brand}", f"7 instead of t in {brand}"),
            (f"8{brand}", f"8 instead of b in {brand}"),
            (f"9{brand}", f"9 instead of g in {brand}"),
            # Additional common typosquatting patterns
            (f"{brand[0]}0{brand[1:]}", f"{brand} with 0 instead of o"),
            (f"{brand[0]}1{brand[1:]}", f"{brand} with 1 instead of i"),
            (f"{brand[0]}3{brand[1:]}", f"{brand} with 3 instead of e"),
            (f"{brand[0]}4{brand[1:]}", f"{brand} with 4 instead of a"),
            (f"{brand[0]}5{brand[1:]}", f"{brand} with 5 instead of s"),
            (f"{brand[0]}7{brand[1:]}", f"{brand} with 7 instead of t"),
            (f"{brand[0]}8{brand[1:]}", f"{brand} with 8 instead of b"),
            (f"{brand[0]}9{brand[1:]}", f"{brand} with 9 instead of g"),
        ]
        
        for pattern, description in typosquatting_patterns:
            if pattern in domain_lower:
                risk_score += 10
                reasons.append(f"Domain '{domain}' appears to be typosquatting: {description}")
                break
                
        # 3. Edit distance check (existing logic)
        if edit_distance(brand, domain_lower) <= 2 and brand not in domain_lower:
            risk_score += 8
            reasons.append(f"Domain '{domain}' is very similar to '{brand}' (typosquatting)")
            continue
            
        # 4. Check for missing/extra characters and character substitutions
        if len(domain_lower) >= len(brand) - 1 and len(domain_lower) <= len(brand) + 2:
            if brand in domain_lower or any(brand[i:i+3] in domain_lower for i in range(len(brand)-2)):
                risk_score += 6
                reasons.append(f"Domain '{domain}' suspiciously similar to '{brand}'")
                continue
                
        # 5. Check for character substitutions within the domain
        for i in range(len(brand)):
            for num, letter in char_substitutions.items():
                # Check if domain has number where brand has letter
                if (i < len(domain_lower) and 
                    brand[i] == letter and 
                    domain_lower[i] == num and
                    domain_lower[:i] + letter + domain_lower[i+1:] == brand):
                    risk_score += 8
                    reasons.append(f"Domain '{domain}' uses '{num}' instead of '{letter}' to impersonate '{brand}'")
                    break
            if risk_score > 0:
                break
                
        # 6. Check for letter-to-number substitutions (reverse of above)
        for i in range(len(domain_lower)):
            for num, letter in char_substitutions.items():
                # Check if domain has letter where brand has number
                if (i < len(brand) and 
                    domain_lower[i] == letter and 
                    brand[i] == num and
                    brand[:i] + letter + brand[i+1:] == domain_lower):
                    risk_score += 8
                    reasons.append(f"Domain '{domain}' uses '{letter}' instead of '{num}' to impersonate '{brand}'")
                    break
            if risk_score > 0:
                break
                
        # 7. Check for partial brand matches with substitutions
        if len(domain_lower) >= 3:  # Minimum length for meaningful comparison
            for i in range(len(brand) - 2):  # Check 3-character substrings
                brand_substring = brand[i:i+3]
                if len(brand_substring) == 3:
                    for j in range(len(domain_lower) - 2):
                        domain_substring = domain_lower[j:j+3]
                        if len(domain_substring) == 3:
                            # Check for single character substitution
                            if sum(a != b for a, b in zip(brand_substring, domain_substring)) == 1:
                                for k, (b_char, d_char) in enumerate(zip(brand_substring, domain_substring)):
                                    if b_char != d_char:
                                        for num, letter in char_substitutions.items():
                                            if (b_char == letter and d_char == num) or (b_char == num and d_char == letter):
                                                risk_score += 6
                                                reasons.append(f"Domain '{domain}' appears to substitute characters to mimic '{brand}'")
                                                break
                                        if risk_score > 0:
                                            break
                                if risk_score > 0:
                                    break
                    if risk_score > 0:
                        break
                        
        # 8. Check for common typosquatting patterns with fuzzy matching
        if len(domain_lower) >= 4 and len(brand) >= 4:
            # Check if domain contains most of the brand name with substitutions
            brand_chars = set(brand)
            domain_chars = set(domain_lower)
            
            # Check for character substitutions
            substitutions_found = 0
            for num, letter in char_substitutions.items():
                if letter in brand and num in domain_lower:
                    substitutions_found += 1
                if num in brand and letter in domain_lower:
                    substitutions_found += 1
            
            # If we find character substitutions and domain is similar length
            if substitutions_found > 0 and abs(len(domain_lower) - len(brand)) <= 2:
                # Check if domain contains significant portion of brand
                brand_in_domain = sum(1 for char in brand if char in domain_lower)
                if brand_in_domain >= len(brand) * 0.6:  # At least 60% of brand characters present
                    risk_score += 7
                    reasons.append(f"Domain '{domain}' appears to be typosquatting '{brand}' with character substitutions")
                    
        # 9. Check for specific common typosquatting patterns
        common_typosquatting = {
            'amazon': ['amzan', 'amaz0n', 'amz0n', 'amaz0n', 'amz0n'],
            'google': ['g00gle', 'g0ogle', 'go0gle', 'g00gle', 'g0ogle'],
            'facebook': ['faceb00k', 'faceb0ok', 'faceb00k', 'faceb0ok'],
            'apple': ['app1e', 'app1e', 'app1e'],
            'microsoft': ['micr0s0ft', 'micr0soft', 'micr0s0ft'],
            'netflix': ['netf1ix', 'netf1x', 'netf1ix'],
            'paypal': ['paypa1', 'payp4l', 'paypa1'],
            'instagram': ['1nstagram', 'inst4gram', '1nstagram'],
            'twitter': ['tw1tter', 'tw1ter', 'tw1tter'],
            'linkedin': ['1inkedin', 'linked1n', '1inkedin']
        }
        
        if brand in common_typosquatting:
            for typo in common_typosquatting[brand]:
                if typo in domain_lower:
                    risk_score += 10
                    reasons.append(f"Domain '{domain}' uses common typosquatting pattern '{typo}' to impersonate '{brand}'")
                    break
    
    return risk_score, reasons

def load_malicious_domains():
    domains = set(rules.MALICIOUS_DOMAINS)
    try:
        if os.path.exists(MALICIOUS_DOMAINS_PATH):
            with open(MALICIOUS_DOMAINS_PATH, 'r', encoding='utf-8') as f:
                external_domains = {line.strip() for line in f if line.strip()}
            domains.update(external_domains)
    except Exception as e:
        logging.error(f"Error loading malicious domains file: {e}")
    return domains

ALL_MALICIOUS_DOMAINS = load_malicious_domains()

def get_contextual_override(text: str, links: list) -> (str, str):
    clean_text = text.lower()
    sender_id_match = re.match(r"^[a-zA-Z]{2}-([a-zA-Z0-9_]+):", text)
    if sender_id_match:
        sender_id = sender_id_match.group(1)
        if any(official_id.lower() == sender_id.lower() for official_id in rules.OFFICIAL_SENDER_IDS):
            return ("Safe", f"Message is from a trusted sender ID: {sender_id}")
    for link in links:
        domain = urlparse(link).netloc
        if domain and any(domain.endswith(safe_ext) for safe_ext in rules.OFFICIAL_DOMAIN_EXTENSIONS):
            return ("Safe", f"Message contains a trusted official domain: {domain}")
    return (None, None)

def check_phishtank(link: str) -> (int, str):
    """
    Checks the URL against PhishTank database for known phishing sites.
    Returns a risk score and reason.
    """
    try:
        api_url = f"http://phishtank.com/checkurl/"
        data = {'url': link, 'format': 'json'}
        response = requests.post(api_url, data=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('results', {}).get('in_database', False):
                verified = result['results'].get('verified', False)
                if verified:
                    return 20, f"This link is confirmed as a phishing site by PhishTank."
                else:
                    return 10, f"This link is reported as suspicious on PhishTank."
    except Exception as e:
        logging.warning(f"PhishTank check failed for {link}: {e}")
    return 0, ""

def check_link_tls(link: str) -> (int, str):
    try:
        domain = urlparse(link).netloc
        if not domain:
            return 0, ""
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                protocol_version = ssock.version()
                if protocol_version in ["TLSv1.1", "TLSv1.0", "SSLv3"]:
                    return 5, rules.FRIENDLY_REASONS["INSECURE_PROTOCOL"]
                expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                if expiry_date < datetime.utcnow():
                    return 8, rules.FRIENDLY_REASONS["EXPIRED_CERT"]
    except ssl.SSLCertVerificationError:
        return 8, rules.FRIENDLY_REASONS["INVALID_CERT"]
    except (socket.timeout, socket.gaierror, ConnectionRefusedError):
        return 0, ""
    except Exception:
        return 1, f"Could not perform TLS check on link: {domain}"
    return 0, ""

def analyse_link_advanced(link: str) -> (int, list):
    risk_score = 0
    reasons = []
    final_url = link
    try:
        domain = urlparse(link).netloc
        shortener_pattern = rules.WEIGHTED_SUSPICIOUS_PATTERNS["SHORTENED_URL"][0]
        if re.search(shortener_pattern, domain, re.IGNORECASE):
            try:
                with requests.Session() as session:
                    session.headers.update({'User-Agent': 'Mozilla/5.0'})
                    resp = session.head(link, allow_redirects=True, timeout=5)
                    final_url = resp.url
                    reasons.append(f"URL shortener '{link}' redirects to: {final_url}")
            except requests.RequestException:
                risk_score += 4
                reasons.append(rules.FRIENDLY_REASONS["UNRESOLVED_SHORTENER"].format(detail=link))
                return risk_score, reasons
        final_domain = urlparse(final_url).netloc
        decoded_domain = decode_punycode(final_domain)
        if any(decoded_domain.endswith(safe_ext) for safe_ext in rules.OFFICIAL_DOMAIN_EXTENSIONS):
            return 0, []
        phishtank_score, phishtank_reason = check_phishtank(final_url)
        if phishtank_score > 0:
            risk_score += phishtank_score
            reasons.append(phishtank_reason)
        try:
            ipaddress.ip_address(final_domain)
            risk_score += 8
            reasons.append(rules.FRIENDLY_REASONS["IP_AS_DOMAIN"])
        except ValueError:
            pass
        if decoded_domain in ALL_MALICIOUS_DOMAINS or final_domain in ALL_MALICIOUS_DOMAINS:
            risk_score += 15
            reasons.append(rules.FRIENDLY_REASONS["MALICIOUS_DOMAIN"].format(detail=final_domain))
        if final_domain != decoded_domain:
            for brand_domain in rules.TARGET_BRAND_DOMAINS:
                if brand_domain in decoded_domain:
                    risk_score += 15
                    reasons.append(f"Domain uses punycode to impersonate '{brand_domain}': {final_domain}")
                    break
        # Enhanced typosquatting detection
        typosquatting_score, typosquatting_reasons = detect_typosquatting(final_domain, rules.TARGET_BRAND_DOMAINS)
        if typosquatting_score > 0:
            risk_score += typosquatting_score
            reasons.extend(typosquatting_reasons)
        if final_url.startswith("https://"):
            tls_score, tls_reason = check_link_tls(final_url)
            if tls_score > 0:
                risk_score += tls_score
                reasons.append(tls_reason)
    except Exception as e:
        reasons.append(f"An error occurred during advanced link analysis: {e}")
    return risk_score, reasons

def analyse_message(text: str) -> dict:
    logging.info(f"Starting analysis for message: {text[:100]}...")
    risk_score = 0
    reasons = []
    links = utils.extract_links(text)
    override_level, override_reason = get_contextual_override(text, links)
    if override_level == "Safe":
        return {
            "level": LEVEL_SAFE,
            "score": 0,
            "reasons": [override_reason],
            "links": links
        }
    clean_text = text.lower()
    text_without_links = clean_text
    for link in links:
        text_without_links = text_without_links.replace(link.lower(), " ")
    for keyword, weight in rules.SCAM_KEYWORDS.items():
        if keyword in text_without_links:
            risk_score += weight
            reasons.append(rules.FRIENDLY_REASONS["SCAM_KEYWORD"].format(detail=keyword))
    high_threat_pattern_found = False
    for pattern_name, (regex, weight) in rules.WEIGHTED_SUSPICIOUS_PATTERNS.items():
        if "URL" not in pattern_name and "DOMAIN" not in pattern_name:
            if re.search(regex, text_without_links, re.IGNORECASE):
                risk_score += weight
                reasons.append(rules.FRIENDLY_REASONS.get(pattern_name, f"Detected pattern: {pattern_name}"))
                if pattern_name == "PERSONAL_INFO_REQUEST":
                    high_threat_pattern_found = True
    # Check for typosquatting in links first
    if links:
        reasons.append(f"Message contains {len(links)} link(s): {', '.join(links)}")
        for link in links:
            domain_patterns_to_check = ["SUSPICIOUS_DOMAIN_TLD", "SHORTENED_URL"]
            for pattern_name in domain_patterns_to_check:
                regex, weight = rules.WEIGHTED_SUSPICIOUS_PATTERNS[pattern_name]
                if re.search(regex, link, re.IGNORECASE):
                    risk_score += weight
                    reasons.append(rules.FRIENDLY_REASONS.get(pattern_name, f"Link pattern: {pattern_name}"))
            link_score, link_reasons = analyse_link_advanced(link)
            if link_score > 0:
                risk_score += link_score
                reasons.extend(link_reasons)
    
    # Apply safe keywords only if no high-threat patterns or typosquatting detected
    if not high_threat_pattern_found and not any('typosquatting' in reason.lower() or 'impersonat' in reason.lower() for reason in reasons):
        for keyword, weight in rules.SAFE_KEYWORDS.items():
            if keyword in text_without_links:
                risk_score += weight
                reasons.append(f"Message contains a known safe keyword: '{keyword}' (Score adjusted)")
    
    if ML_MODEL and VECTORIZER:
        try:
            vectorized_text = VECTORIZER.transform([text_without_links])
            scam_probability = ML_MODEL.predict_proba(vectorized_text)[0][1]
            if scam_probability > 0.9:
                risk_score += 8
                reasons.append(rules.FRIENDLY_REASONS["ML_CONFIDENCE"])
            elif scam_probability > 0.5:
                risk_score += 0
                # Only add reason if there are other suspicious indicators
                if risk_score > 0:
                    reasons.append(rules.FRIENDLY_REASONS["ML_CONFIDENCE"])
        except Exception as e:
            reasons.append(f"Error during ML model prediction: {e}")
    risk_score = int(risk_score)
    if risk_score >= config.RISK_THRESHOLDS['DANGEROUS']:
        risk_level = LEVEL_DANGEROUS
    elif risk_score >= config.RISK_THRESHOLDS['SUSPICIOUS']:
        risk_level = LEVEL_SUSPICIOUS
    else:
        risk_level = LEVEL_SAFE
    logging.info(f"Analysis complete. Level: {risk_level}, Score: {risk_score}, Reasons: {len(reasons)}")
    return {
        "level": risk_level,
        "score": risk_score,
        "reasons": reasons,
        "links": links
    }
