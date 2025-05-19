"""Speech-to-text tool for converting audio to text."""

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
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not configured. Cannot perform speech-to-text.")
        return None

    try:
        # Decode base64 to binary
        audio_binary = base64.b64decode(base64_audio)

        # Use OpenAI Whisper API
        temp_file = "temp_audio.m4a"  # Assuming m4a, adjust if needed
        try:
            with open(temp_file, "wb") as f:
                f.write(audio_binary)

            # Call the Whisper API
            with open(temp_file, "rb") as audio_file_handle:
                # Note: The openai library might have changed. 
                # This is based on common usage for v0.x. For v1.x, it's different.
                # Assuming openai client is already initialized if needed for v1.x
                transcript_response = await openai.Audio.atranscribe(
                    model="whisper-1", 
                    file=audio_file_handle
                )
            
            # Accessing transcription text and log probabilities can vary by OpenAI library version
            # For older versions (like 0.28), it might be directly in transcript_response
            # For newer versions (1.x), it might be transcript_response.text
            # This part might need adjustment based on your specific openai library version
            transcribed_text = transcript_response.get("text") # More robust for dict-like response
            avg_logprob = transcript_response.get("avg_logprob") # For older versions

            # Check confidence (avg_logprob might not be available in newer openai lib versions directly)
            # This confidence check might need to be removed or adapted if using openai >= 1.0
            if avg_logprob is not None and avg_logprob < -1.0:  # Low confidence threshold
                logger.warning(f"Low confidence in speech transcription. avg_logprob: {avg_logprob}")
                # Depending on strictness, you might still return the text or None
                # return None 

            if not transcribed_text:
                logger.warning("Speech transcription resulted in empty text.")
                return None

            return transcribed_text

        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

    except openai.APIError as e:
        logger.error(f"OpenAI API error during speech to text conversion: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"General error in speech to text conversion: {str(e)}")
        return None