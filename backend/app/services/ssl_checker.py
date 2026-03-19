import socket
import ssl
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from app.logger import logger
from typing import Dict, Any, Optional

def get_ssl_details(hostname: str) -> dict:
    """Analyze SSL certificate of a hostname."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=3.0) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert_bin = ssock.getpeercert(binary_form=True)
                cert = x509.load_der_x509_certificate(cert_bin, default_backend())
                
                # Extract details
                issuer = cert.issuer.rfc4514_string()
                valid_from = cert.not_valid_before_utc
                valid_to = cert.not_valid_after_utc
                subject = cert.subject.rfc4514_string()
                
                # Check age
                age_hours = (datetime.now(valid_from.tzinfo) - valid_from).total_seconds() / 3600
                
                return {
                    "ssl_valid": True,
                    "issuer": issuer,
                    "subject": subject,
                    "valid_from": valid_from.isoformat(),
                    "valid_to": valid_to.isoformat(),
                    "cert_age_hours": age_hours,
                    "is_self_signed": issuer == subject
                }
    except Exception as e:
        logger.error(f"SSL check failed for {hostname}: {e}")
        return {
            "ssl_valid": False,
            "error": str(e)
        }
