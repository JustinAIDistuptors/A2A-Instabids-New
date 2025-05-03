"""
Speech-to-text tool using OpenAI Whisper API with log probability guard.

This module provides a function to transcribe audio using OpenAI's Whisper model
and filters out potential hallucinations based on log probability thresholds.
"""
import openai
import os
import base64
import tempfile
import logging
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Log probability threshold for filtering out hallucinations
# ≈ 0.85 average probability per token
LOGPROB_THRESH = -1.8

async def speech_to_text(b64_audio: str) -> Optional[str]:
    """
    Transcribe base64-encoded audio using OpenAI's Whisper model.
    
    Args:
        b64_audio: Base64-encoded audio data
        
    Returns:
        Transcribed text if confidence is high enough, None otherwise
        
    Raises:
        Exception: If transcription fails
    """
    try:
        # Create temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            # Decode and write the audio data
            tf.write(base64.b64decode(b64_audio))
            tf.flush()
            
            # Call Whisper API
            resp = await openai.Audio.atranscribe(
                "whisper-1",
                open(tf.name, "rb"),
                logprobs=True,  # returns per-token logprobs
            )
            
            # Clean up the temporary file
            os.unlink(tf.name)
        
        # Filter out potential hallucinations based on log probability
        if resp["avg_logprob"] < LOGPROB_THRESH:
            logger.warning(
                f"Transcription rejected due to low confidence: {resp['avg_logprob']} < {LOGPROB_THRESH}"
            )
            return None
            
        logger.info(f"Transcription accepted with confidence: {resp['avg_logprob']}")
        return resp["text"]
        
    except Exception as e:
        logger.error(f"Speech-to-text transcription failed: {str(e)}")
        raise