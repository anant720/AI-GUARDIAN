"""
phase9/alerting.py
───────────────────
Handles external developer notifications.
Currently mocks external Webhook/Email delivery via logging.
Can easily be integrated with SendGrid or Jira APIs.
"""
import os
import httpx
import logging
from app.logger import logger

_FAILURE_WEBHOOK = os.getenv("FAILURE_WEBHOOK")
_FAILURE_EMAIL = os.getenv("FAILURE_EMAIL")

async def send_dev_alert(subject: str, message: str, severity: str = "ERROR"):
    """
    Sends a critical alert to the DevOps/Maintenance team.
    Called when Self-Healing fails.
    """
    logger.critical(f"Self-Healing & System Monitoring DEVELOPER ALERT: [{severity}] {subject} - {message}")

    payload = {
        "text": f"*{subject}*\n{message}\nSeverity: {severity}"
    }

    if _FAILURE_WEBHOOK:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(_FAILURE_WEBHOOK, json=payload, timeout=3.0)
        except Exception as e:
            logger.error(f"Failed to push developer webhook: {e}")

    if _FAILURE_EMAIL:
        # Mocking SMTP gateway integration
        logger.debug(f"Mocking email delivery to {_FAILURE_EMAIL} for alert: {subject}")
