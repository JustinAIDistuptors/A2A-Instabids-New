"""SendGrid e‑mail stub (real send Sprint 7)."""
from __future__ import annotations
import os, json
from typing import Dict, Any
import logging

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail
except ImportError:
    logging.warning("SendGrid library not installed. Email sending will be stubbed.")
    sendgrid = None # type: ignore
    Mail = None # type: ignore

# Load credentials from environment variables with defaults for stubbing
_KEY = os.getenv("SENDGRID_API_KEY", "stub")
_SENDER = os.getenv("SUPPORT_EMAIL", "no-reply@example.com") # Use a generic example

def send_email(to: str, subject: str, html: str, meta: Dict[str, Any] | None = None) -> str:
    """Sends an email using SendGrid or returns 'stub-id' if stubbed.

    Args:
        to: The recipient email address.
        subject: The email subject line.
        html: The HTML content of the email.
        meta: Optional metadata (not used by SendGrid send).

    Returns:
        The SendGrid message ID ('X-Message-Id' header) on success, 
        'stub-id' if stubbed, or 'unknown-id' if header is missing.
        
    Raises:
        RuntimeError: If SendGrid client cannot be initialized or sending fails.
    """
    if _KEY == "stub" or not sendgrid or not Mail:
        logging.info(f"STUB: Sending email to {to} | Subject: {subject}")
        # Log a snippet of HTML for debugging if needed
        # logging.debug(f"HTML Body Snippet: {html[:100]}...") 
        return "stub-id"
    
    try:
        sg = sendgrid.SendGridAPIClient(api_key=_KEY)
        message = Mail(
            from_email=_SENDER,
            to_emails=to,
            subject=subject,
            html_content=html
        )
        logging.info(f"Sending email via SendGrid to {to} | Subject: {subject}")
        response = sg.send(message)
        
        # Check response status code for success (e.g., 2xx)
        if 200 <= response.status_code < 300:
            msg_id = response.headers.get("X-Message-Id", "unknown-id")
            logging.info(f"Email sent successfully. Status: {response.status_code}, Message ID: {msg_id}")
            return msg_id
        else:
            # Log error details from SendGrid response body if available
            logging.error(f"SendGrid API error. Status: {response.status_code}, Body: {response.body}")
            raise RuntimeError(f"SendGrid API failed with status {response.status_code}")

    except Exception as e:
        logging.error(f"Failed to send SendGrid email to {to}: {e}")
        raise RuntimeError(f"Failed to send SendGrid email: {e}") from e
