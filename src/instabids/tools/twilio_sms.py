"""Twilio SMS stub (real send wired up Sprint 7)."""
from __future__ import annotations
import os
from typing import Dict, Any
import logging

try:
    from twilio.rest import Client
except ImportError:
    logging.warning("Twilio library not installed. SMS sending will be stubbed.")
    Client = None # type: ignore

# Load credentials from environment variables with defaults for stubbing
_ACCOUNT = os.getenv("TWILIO_ACCOUNT_SID", "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX") # Use valid format placeholder
_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "stub")
_FROM    = os.getenv("TWILIO_FROM_NUMBER", "+15005550006") # Twilio magic number for testing

_client: Client | None = None

def _lazy() -> Client:
    """Lazy initializes and returns the Twilio client."""
    global _client
    if _client is None:
        if not Client: # Check if import failed
            raise RuntimeError("Twilio SDK not available. Cannot create client.")
        if _TOKEN != "stub":
            try:
                _client = Client(_ACCOUNT, _TOKEN)
            except Exception as e:
                 logging.error(f"Failed to initialize Twilio client: {e}")
                 raise RuntimeError(f"Failed to initialize Twilio client: {e}") from e
        else:
             # In stub mode, maybe return a mock client or handle differently
             # For now, we rely on the send_sms check
             pass
    if _client is None and _TOKEN != "stub":
        # Should not happen if initialization succeeded, but as a safeguard
        raise RuntimeError("Twilio client could not be initialized.")
    # If still in stub mode, _client might remain None, handled in send_sms
    return _client # type: ignore

def send_sms(to: str, body: str, meta: Dict[str, Any] | None = None) -> str:
    """Sends an SMS using Twilio or returns 'stub-sid' if stubbed.
    
    Args:
        to: The recipient phone number (E.164 format).
        body: The message content.
        meta: Optional metadata (not used by Twilio send).

    Returns:
        The Twilio message SID on success, or 'stub-sid' if stubbed.
        
    Raises:
        RuntimeError: If Twilio client cannot be initialized or sending fails.
    """
    if _TOKEN == "stub" or not Client:
        logging.info(f"STUB: Sending SMS to {to}: {body}")
        return "stub-sid"
    
    try:
        client_instance = _lazy()
        # Ensure we have a client instance before proceeding
        if not client_instance:
            raise RuntimeError("Twilio client not available for sending SMS.")
        
        logging.info(f"Sending SMS via Twilio to {to}")
        msg = client_instance.messages.create(
            body=body, 
            from_=_FROM, 
            to=to
        )
        logging.info(f"SMS sent successfully. SID: {msg.sid}")
        return msg.sid
    except Exception as e:
        logging.error(f"Failed to send Twilio SMS to {to}: {e}")
        # Depending on requirements, either raise or return an error indicator
        # Raising allows upstream handlers to manage the failure.
        raise RuntimeError(f"Failed to send Twilio SMS: {e}") from e
