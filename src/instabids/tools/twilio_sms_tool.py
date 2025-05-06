"""Send SMS via Twilio – outbound recruiting tool implementation."""
from __future__ import annotations
import os
import logging
from typing import Dict, Any

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
except ImportError:
    logging.critical("Twilio SDK not installed. Run 'pip install twilio'")
    # Define dummy classes/functions if you want the app to run without crashing
    # but this is a critical dependency for this tool.
    Client = None # type: ignore 
    TwilioRestException = Exception # type: ignore

log = logging.getLogger(__name__)

# Configuration - Ensure these are set in your environment
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM") # Twilio phone number or Messaging Service SID

_client: Client | None = None
_initialized = False

def _get_client() -> Client:
    """Initializes and returns the Twilio client. Raises RuntimeError if config is missing."""
    global _client, _initialized
    if not _initialized:
        if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM]):
            log.error("Twilio credentials (TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM) not fully configured.")
            raise RuntimeError("Twilio credentials not configured.")
        if not Client:
            log.critical("Twilio SDK is not available.")
            raise RuntimeError("Twilio SDK failed to import.")
        try:
            _client = Client(TWILIO_SID, TWILIO_TOKEN)
            log.info("Twilio client initialized successfully.")
        except Exception as e:
            log.exception("Failed to initialize Twilio client:", exc_info=e)
            raise RuntimeError(f"Failed to initialize Twilio client: {e}") from e
        _initialized = True
        
    if not _client:
         # This should not happen if initialization succeeded, but acts as a safeguard
         raise RuntimeError("Twilio client is not available.")
         
    return _client

def send_sms(to: str, body: str) -> Dict[str, Any]:
    """Sends an SMS using the configured Twilio client.

    Args:
        to: The recipient phone number (E.164 format preferred).
        body: The message content.

    Returns:
        A dictionary containing the message SID and status on success.
        Example: {'sid': 'SMxxxxxxxxxx', 'status': 'queued'}
        
    Raises:
        RuntimeError: If sending fails due to configuration or API errors.
    """
    if not to or not body:
        log.error("Cannot send SMS: 'to' and 'body' parameters are required.")
        raise ValueError("Missing 'to' or 'body' for send_sms")
        
    try:
        client = _get_client()
        log.info(f"Attempting to send SMS to {to} from {TWILIO_FROM}")
        msg = client.messages.create(from_=TWILIO_FROM, to=to, body=body)
        log.info(f"SMS submitted successfully. SID: {msg.sid}, Status: {msg.status}")
        return {"sid": msg.sid, "status": msg.status}
    except TwilioRestException as e:
        log.error(f"Twilio API error sending SMS to {to}: {e}")
        # Consider specific error handling based on e.code if needed
        raise RuntimeError(f"Twilio API error: {e}") from e
    except Exception as e:
        # Catch potential client initialization errors or other unexpected issues
        log.exception(f"Unexpected error sending SMS to {to}:", exc_info=e)
        raise RuntimeError(f"Unexpected error sending SMS: {e}") from e
