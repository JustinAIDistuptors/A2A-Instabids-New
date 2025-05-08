"""
Speech-to-text tool for converting audio to text.
"""
from typing import Optional
import base64
import os
import logging
import openai

logger = logging.getLogger(__name__)

# Configure the OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.warning("OPENAI_API_KEY not set in environment variables")

async def speech_to_text(base64_audio: str) -> Optional[str]:
    """
    Convert speech to text using OpenAI's Whisper API.
    
    Args:
        base64_audio: Base64-encoded audio data
        
    Returns:
        Transcribed text or None if failed
    """
    try:
        # Decode base64 to binary
        audio_binary = base64.b64decode(base64_audio)
        
        # Use OpenAI Whisper API
        temp_file = "temp_audio.m4a"
        try:
            with open(temp_file, "wb") as f:
                f.write(audio_binary)
                
            # Call the Whisper API
            with open(temp_file, "rb") as f:
                transcript = await openai.Audio.atranscribe("whisper-1", f)
                
            # Check confidence
            if transcript["avg_logprob"] < -1.0:  # Low confidence threshold
                logger.warning("Low confidence in speech transcription")
                return None
                
            return transcript["text"]
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    except Exception as e:
        logger.error(f"Error in speech to text conversion: {str(e)}")
        return None