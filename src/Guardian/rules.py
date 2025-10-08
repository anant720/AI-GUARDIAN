
SCAM_KEYWORDS = {
    # Urgency & Authority
    "urgent": 2,
    "immediate": 2,
    "action required": 3,
    "account suspended": 3,
    "verify your account": 3,
    "kyc": 3,
    "otp": 6, 
    "one time password": 6,
    "account locked": 4,
    "suspended": 3,
    "blocked": 3,
    "expired": 2,
    "deadline": 2,
    "last chance": 3,
    "final notice": 3,
    "security alert": 3,
    "unusual activity": 3,
    "account compromised": 4,
    "suspicious login": 3,

    # Financial & Prizes
    "lottery": 3,
    "won": 2,
    "prize": 3,
    "free gift": 2,
    "cash prize": 3,
    "refund": 2,
    "delivery fee": 4, # Very common scam
    "shipping fee": 4,
    "customs fee": 4,
    "release parcel": 4,
    "crypto": 2,
    "airdrop": 2,
    "investment": 2,
    "guaranteed return": 3,
    "congratulations": 2,
    "winner": 2,
    "claim now": 3,
    "limited time": 2,
    "exclusive offer": 2,
    "claim your reward": 3,
    "cash bonus": 3,
    "inheritance": 3,
    "tax refund": 3,

    # Job Scams
    "job offer": 2,
    "work from home": 1,
    "guaranteed income": 3,
    "easy money": 3,
    "part time": 1,
    "data entry": 1,
    "online work": 1,
    "earn money": 2,
    "hiring now": 1,
    "no experience required": 2,
    "quick cash": 3,

    # Suspicious Actions
    "click this link": 3,
    "download this app": 3,
    "update your details": 4,
    "confirm your identity": 4,
    "share your": 4,
    "send your": 4,
    "provide your": 4,
    "enter your": 4,
    "verify now": 5,
    "activate now": 4,
    "unlock now": 4,
    "account details": 5,
    "secure your account": 4,
    "update your payment": 4,
    "personal details": 5,
    "bank details": 6,
    "card details": 6,
    "password": 4,
    "login details": 5,

    # Banking & Financial
    "bank account": 2,
    "credit card": 2,
    "debit card": 2,
    "atm": 2,
    "pin": 3,
    "cvv": 4,
    "card number": 4,
    "account number": 3,
    "routing number": 3,
    "ifsc": 2,
    "aadhaar": 3,
    "passport": 2,

    # Social Engineering
    "trust me": 1,
    "don't tell anyone": 2,
    "keep this secret": 2,
    "confidential": 1,
    "private": 1,
    "exclusive": 1,
    "special": 1,
    "limited": 1,
    "today only": 2,
    "act fast": 2,
    "hurry": 2,

    # Tech Support Scams
    "virus detected": 4,
    "malware alert": 4,
    "tech support": 3,
    "remote access": 4,
    "computer infected": 4,
    "your pc is at risk": 4,
    
    # Typosquatting & Domain Impersonation
    "verify your account": 3,
    "account verification": 3,
    "security verification": 3,
    "login verification": 3,
    "identity verification": 4,
    "account compromised": 4,
    "suspicious activity": 3,
    "unusual login": 3,
    "account locked": 4,
    "account suspended": 4,
    "account restricted": 3,
    "security breach": 4,
    "data breach": 4,
    "account hacked": 4,
    "password compromised": 4,
}

# Keywords that can reduce the risk score, indicating a legitimate context.
# The score reduction should be significant enough to counteract common false positives.
SAFE_KEYWORDS = {
    # E-commerce & Delivery
    "myntra": -7,
    "flipkart": -7,
    "amazon": -7,
    "zomato": -7,
    "swiggy": -7,
    "your order": -4,
    "order number": -5,
    "tracking id": -5,
    "delivery executive": -5,

    # Banking (official communication)
    "hdfc bank": -7,
    "icici bank": -7,
    "sbi": -7,
    "state bank of india": -7,
    "transaction alert": -3,
    "do not share": -2, # Often included with legitimate OTPs

    # University & Academic Context
    "university": -3,
    "exam": -2,
    "semester": -2,
    "timetable": -2,
    "assignment": -2,
    "fee payment": -2,
    "office": -1,
    "email": -1,
    "call": -1,
}

# Weighted regular expressions for detecting suspicious patterns.
# Higher weights indicate a stronger likelihood of a scam.
WEIGHTED_SUSPICIOUS_PATTERNS = {
    # High-risk patterns
    "PERSONAL_INFO_REQUEST": (r"(send|share|enter|provide)\s+(your|the)?\s+(otp|one time password|password|pin|ssn|social security number|bank details|aadhaar|pan|card number)", 8),
    "GIFT_CARD_REQUEST": (r"(buy|get|send)\s+(me|us)?\s+(a|an)?\s+(google play|amazon|steam|apple|walmart)\s+gift card", 7),

    # Medium-risk patterns
    "SHORTENED_URL": (r"\b(bit\.ly|t\.co|shorturl|tinyurl|goo\.gl|ow\.ly)\b", 4),
    "SUSPICIOUS_DOMAIN_TLD": (r"\b[a-zA-Z0-9.-]+\.(tk|ml|ga|cf|gq|xyz|top|buzz|live|club|win|loan|work|click|download|verify|update)\b", 4),
    "URGENCY_PATTERN": (r"\b(urgent|immediate|asap|right now|this instant|hurry|quick|fast)\b", 3),

    # Low-risk patterns (indicators that add context but aren't dangerous alone)
    "EXCESSIVE_CAPS": (r"(\b[A-Z]{4,}\b\s*){4,}", 1),
    "EXCESSIVE_PUNCTUATION": (r"[!]{3,}|[?]{3,}", 1), # Increased threshold to 3+
    "PHONE_NUMBER": (r"\b(?:(?:\+91|91|0)\s*[-]?\s*)?[6-9]\d{9}\b|\b0\d{2,4}\s*[-]?\s*\d{6,8}\b", 0), # More general Indian phone numbers (mobile and landline)
    "SUSPICIOUS_NUMBERS": (r"\b((?!19\d{2}|20\d{2})\d{5,}|\d{7,})\b", 1), # 5+ digits (excluding years) or 7+ digits
    "PAN_CARD": (r"\bpan\b", 2), # Specific check for 'pan' as a whole word
    "MONEY_AMOUNT": (r"[₹$€£]\s*\d+", 1),
    
    # Typosquatting patterns
    "TYPOSQUATTING_DOMAIN": (r"\b[a-zA-Z0-9.-]*[0-9][a-zA-Z0-9.-]*\.(com|net|org|info|biz|co|in|tk|ml|ga|cf|gq|xyz|top|buzz|live|club|win|loan|work|click|download|verify|update)\b", 3),
    "NUMBER_SUBSTITUTION": (r"\b(g00gle|g0ogle|go0gle|amaz0n|amz0n|faceb00k|faceb0ok|app1e|app1e|micr0s0ft|micr0soft|netf1ix|netf1x|paypa1|payp4l|1nstagram|inst4gram|tw1tter|tw1ter|1inkedin|linked1n)\b", 4),
    "DOMAIN_IMPERSONATION": (r"\b[a-zA-Z0-9.-]*(google|facebook|amazon|apple|microsoft|netflix|paypal|instagram|twitter|linkedin)[a-zA-Z0-9.-]*\.(tk|ml|ga|cf|gq|xyz|top|buzz|live|club|win|loan|work|click|download|verify|update)\b", 5),
}

# Official sender IDs (common in India) that indicate a message is legitimate.
# This is used for contextual overrides. Case-insensitive.
OFFICIAL_SENDER_IDS = [
    # Banks
    "HDFCBK", "ICICIB", "SBIBNK", "AXISBK", "KOTAKB",
    # Telecom
    "JIOINFO", "AIRTEL", "ViCARE",
    # Delivery & E-commerce
    "FLPKRT", "AMZIND", "MYNTRA", "ZOMATO", "SWIGGY",
    # Government & Utilities
    "GOVIND", "BSEB", "MSEB",
    # Others
    "Google", "Verify"
]

# This is now DEPRECATED in favor of WEIGHTED_SUSPICIOUS_PATTERNS
SUSPICIOUS_PATTERNS = {
    pattern_name: regex for pattern_name, (regex, weight) in WEIGHTED_SUSPICIOUS_PATTERNS.items()
}

# Domains often used for legitimate services, to reduce false positives.
# This is not exhaustive and should be managed carefully.
SAFE_DOMAINS = [
    "google.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "amazon.com",
    "apple.com",
    "microsoft.com",
    "netflix.com",
    "spotify.com",
    "youtube.com",
    "linkedin.com",
    "github.com",
    "paypal.com",
    "dropbox.com",
]

MALICIOUS_DOMAINS = [
    # Fake banking domains
    "verify-account-update.com",
    "secure-login-portal.net",
    "bank-support-service.com",
    "bank-security-update.net",
    "account-verification-now.com",
    "banking-security-alert.org",
    "secure-bank-login.net",
    "online-banking-support.org",
    "bank-resolve-issue.com",
    "bank-account-verify.com",
    
    # Lottery and prize scams
    "free-money-now.org",
    "claim-your-prize-today.info",
    "lottery-winner-claim.net",
    "prize-claim-now.com",
    "free-prize-claim.org",
    "lottery-verification.net",
    "winner-claim-portal.com",
    "instant-win-online.com",
    "claim-your-winnings.net",
    
    # Job scam domains
    "easy-money-jobs.net",
    "work-from-home-scam.com",
    "guaranteed-income-now.org",
    "quick-cash-jobs.net",
    "online-earning-scam.com",
    "remote-work-offer.net",
    "easy-job-apply.com",
    
    # Crypto and investment scams
    "crypto-airdrop-free.net",
    "bitcoin-investment-scam.com",
    "crypto-trading-scam.org",
    "investment-opportunity-scam.net",
    "crypto-giveaway-scam.com",
    "free-bitcoin-now.org",
    "guaranteed-crypto-returns.com",
    
    # Delivery and shipping scams
    "delivery-fee-payment.net",
    "package-release-fee.com",
    "customs-fee-payment.org",
    "shipping-fee-scam.net",
    "delivery-charge-scam.org",
    "track-your-parcel-scam.com",
    "dhl-express-update.net",
    
    # Social media and dating scams
    "facebook-verification-scam.com",
    "facebo0k.com",
    "instagram-account-verify.net",
    "whatsapp-verification-scam.org",
    "dating-site-verification.net",
    "social-media-verification-scam.com",
    
    # Government and authority scams
    "irs-tax-refund-scam.net",
    "government-benefit-scam.com",
    "court-notice-scam.org",
    "police-verification-scam.net",
    "tax-payment-due.com",
    "official-gov-service.org",
    "legal-notice-scam.com",
    
    # Tech support scams
    "microsoft-support-scam.net",
    "apple-support-scam.com",
    "windows-update-scam.org",
    "tech-support-scam.net",
    "computer-virus-scam.com",
    "pc-cleaner-scam.com",
    "antivirus-renewal-scam.net",
    
    # Generic scam domains
    "free-gift-claim.net",
    "survey-reward-scam.com",
    "free-trial-scam.org",
    "subscription-scam.net",
    "verification-scam.com",

    # Domains with suspicious TLDs often used for scams
    "secure-login.click",
    "account-update.link",
    "verify-identity.xyz",
    "bank-support.top",
    "package-tracking.buzz",
    "free-money.club",
    "crypto-giveaway.live",

    # Common patterns for phishing
    "login-apple-id.com",
    "microsoft-secure.net",
    "amazon-support-service.org",
    "netflix-account-update.info",
    "paypal-secure-payment.com",
    "your-bank-security.com",
    "dhl-delivery-update.com",

    # Typosquatting examples
    "amaz0n-support.com",
    "g00gle-security.net",
    "microsft-support.org"
]

# Official domain extensions that indicate legitimacy
# This is used for contextual overrides.
OFFICIAL_DOMAIN_EXTENSIONS = [
    ".gov.in", ".gov",
    ".edu.in", ".edu",
    ".ac.in", ".ac.uk"
]

# Domains of popular brands to check for impersonation (typosquatting).
# The detection logic will check if a suspicious link is trying to look like one of these.
TARGET_BRAND_DOMAINS = [
    # Tech Giants
    "google.com", "facebook.com", "instagram.com", "whatsapp.com", 
    "twitter.com", "linkedin.com", "youtube.com", "tiktok.com",
    
    # E-commerce
    "amazon.com", "flipkart.com", "myntra.com", "snapdeal.com",
    "paytm.com", "phonepe.com", "gpay.com",
    
    # Streaming & Entertainment
    "netflix.com", "spotify.com", "primevideo.com", "hotstar.com",
    
    # Banking & Finance
    "hdfcbank.com", "icicibank.com", "onlinesbi.sbi", "axisbank.com",
    "paypal.com", "razorpay.com", "phonepe.com",
    
    # Tech Companies
    "apple.com", "microsoft.com", "adobe.com", "oracle.com",
    
    # Food & Delivery
    "zomato.com", "swiggy.com", "ubereats.com", "dominos.com",
    
    # Travel & Transport
    "makemytrip.com", "goibibo.com", "uber.com", "ola.com",
    
    # Government & Official
    "gov.in", "uidai.gov.in", "incometax.gov.in",
    
    # Social & Communication
    "telegram.org", "discord.com", "zoom.us", "skype.com"
]

# User-friendly explanations for why something was flagged.
FRIENDLY_REASONS = {
    # Keywords
    "SCAM_KEYWORD": "Message has suspicious words like '{detail}' that scammers often use.",

    # Regex Patterns
    "PERSONAL_INFO_REQUEST": "Message asks for private info like passwords or OTPs - big warning sign!",
    "GIFT_CARD_REQUEST": "Asks you to buy gift cards. Scammers love this because it's hard to track.",
    "SHORTENED_URL": "Link is shortened (like bit.ly). It hides where it really goes.",
    "SUSPICIOUS_DOMAIN_TLD": "Link ends with weird stuff like .xyz. Fake sites often use these.",
    "URGENCY_PATTERN": "Tries to rush you with words like 'urgent' or 'now'. Don't panic!",
    "EXCESSIVE_CAPS": "Lots of BIG LETTERS. Scammers shout to scare you.",
    "EXCESSIVE_PUNCTUATION": "Too many !!! or ???. Looks unprofessional, like a scam.",

    # Advanced Link Analysis
    "IMPERSONATION": "Link '{detail}' looks like it copies '{brand}'. Double-check the address!",
    "IP_AS_DOMAIN": "Link goes to a number (IP) instead of a name like google.com. Very fishy.",
    "MALICIOUS_DOMAIN": "Link '{detail}' is known for being bad. Stay away!",
    "UNRESOLVED_SHORTENER": "Short link '{detail}' won't open. Probably hiding something bad.",
    "INSECURE_PROTOCOL": "Site uses old security. Real sites keep things safe and updated.",
    "EXPIRED_CERT": "Site's safety badge is out of date. Legit sites renew this.",
    "INVALID_CERT": "Site's safety is broken. Connection isn't secure - don't trust it.",
    
    # Typosquatting Detection
    "TYPOSQUATTING_DOMAIN": "Domain has numbers mixed in - scammers use this to trick you!",
    "NUMBER_SUBSTITUTION": "Domain uses numbers instead of letters to look like a real site. Classic scam trick!",
    "DOMAIN_IMPERSONATION": "Domain tries to copy a famous brand name. Don't fall for it!",

    # ML Model
    "ML_CONFIDENCE": "Our smart AI thinks this looks exactly like scam messages it's seen before."
}
