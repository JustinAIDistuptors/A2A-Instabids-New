"""Send email invites via Twilio SendGrid – tool implementation."""
from __future__ import annotations
import os
import logging
from typing import Dict, Any

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, From, To, Subject, Content
except ImportError:
    logging.critical("SendGrid SDK not installed. Run 'pip install sendgrid'")
    SendGridAPIClient = None # type: ignore
    Mail = None # type: ignore

log = logging.getLogger(__name__)

# Configuration - Ensure these are set in your environment
SENDGRID_KEY = os.getenv("SENDGRID_KEY")
# Default sender, can be overridden if needed
DEFAULT_FROM_EMAIL = os.getenv("SUPPORT_EMAIL", "noreply@instabids.com") 

_sg: SendGridAPIClient | None = None
_initialized = False

def _get_client() -> SendGridAPIClient:
    """Initializes and returns the SendGrid client. Raises RuntimeError if config is missing."""
    global _sg, _initialized
    if not _initialized:
        if not SENDGRID_KEY:
            log.error("SendGrid API Key (SENDGRID_KEY) is not configured.")
            raise RuntimeError("SendGrid API Key not configured.")
        if not SendGridAPIClient:
             log.critical("SendGrid SDK is not available.")
             raise RuntimeError("SendGrid SDK failed to import.")
        try:
            _sg = SendGridAPIClient(SENDGRID_KEY)
            log.info("SendGrid client initialized successfully.")
        except Exception as e:
            log.exception("Failed to initialize SendGrid client:", exc_info=e)
            raise RuntimeError(f"Failed to initialize SendGrid client: {e}") from e
        _initialized = True
        
    if not _sg:
         # Safeguard
         raise RuntimeError("SendGrid client is not available.")
         
    return _sg

def send_email(to: str, subject: str, html: str, from_email: str | None = None) -> str:
    """Sends an email using the configured SendGrid client.

    Args:
        to: The recipient email address.
        subject: The email subject line.
        html: The HTML content of the email.
        from_email: Optional sender email address. Defaults to SUPPORT_EMAIL env var or 'noreply@instabids.com'.

    Returns:
        A string indicating success status and response code (e.g., 'sg:202').
        
    Raises:
        ValueError: If required parameters are missing.
        RuntimeError: If sending fails due to configuration or API errors.
    """
    if not to or not subject or not html:
        log.error("Cannot send email: 'to', 'subject', and 'html' parameters are required.")
        raise ValueError("Missing required parameters for send_email")

    sender = from_email or DEFAULT_FROM_EMAIL
    
    # Basic validation
    if '@' not in to or '@' not in sender:
        log.error(f"Invalid email format provided. To: {to}, From: {sender}")
        raise ValueError("Invalid email format")

    message = Mail(
        from_email=sender,
        to_emails=to,
        subject=subject,
        html_content=html
    )
    
    try:
        sg_client = _get_client()
        log.info(f"Attempting to send email to {to} from {sender} with subject '{subject}'")
        response = sg_client.send(message)
        status_code = response.status_code
        
        log.info(f"SendGrid response status code: {status_code}")
        # Consider logging response headers or body on non-2xx status for debugging
        if not (200 <= status_code < 300):
             log.error(f"SendGrid API error. Status: {status_code}, Body: {response.body}, Headers: {response.headers}")
             # Raise an error for non-successful responses
             raise RuntimeError(f"SendGrid API request failed with status code {status_code}")
             
        # Return status code for confirmation
        return f"sg:{status_code}" 
        
    except Exception as e:
        # Catch potential client init errors, API errors, or other issues
        log.exception(f"Failed to send SendGrid email to {to}:", exc_info=e)
        # Re-raise as a RuntimeError for consistent error handling upstream
        if isinstance(e, RuntimeError):
             raise e # Re-raise existing RuntimeErrors (like config errors)
        else:
             raise RuntimeError(f"Failed to send SendGrid email: {e}") from e
