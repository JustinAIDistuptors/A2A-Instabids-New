"""
Unit tests for the speech-to-text tool.
"""
import pytest
import base64
import os
from unittest.mock import patch, AsyncMock, MagicMock
from instabids.tools.stt_tool import speech_to_text, LOGPROB_THRESH

# Sample base64 audio (this is just a placeholder, not actual audio)
SAMPLE_AUDIO = "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="

@pytest.mark.asyncio
async def test_speech_to_text_success():
    """Test successful transcription with high confidence."""
    # Mock the OpenAI API call
    with patch('instabids.tools.stt_tool.openai.Audio.atranscribe', new_callable=AsyncMock) as mock_transcribe, \
         patch('instabids.tools.stt_tool.tempfile.NamedTemporaryFile') as mock_temp, \
         patch('instabids.tools.stt_tool.os.unlink'):
        
        # Set up the mock response with high confidence
        mock_transcribe.return_value = {
            "text": "Need roof repair, budget around $8000",
            "avg_logprob": -1.0,  # High confidence (better than threshold)
        }
        
        # Set up mock temp file
        mock_file = MagicMock()
        mock_temp.return_value.__enter__.return_value = mock_file
        
        # Call the function
        result = await speech_to_text(SAMPLE_AUDIO)
        
        # Verify the result
        assert result == "Need roof repair, budget around $8000"
        
        # Verify the API was called correctly
        mock_transcribe.assert_called_once()
        mock_file.write.assert_called_once()

@pytest.mark.asyncio
async def test_speech_to_text_low_confidence():
    """Test transcription rejection due to low confidence."""
    # Mock the OpenAI API call
    with patch('instabids.tools.stt_tool.openai.Audio.atranscribe', new_callable=AsyncMock) as mock_transcribe, \
         patch('instabids.tools.stt_tool.tempfile.NamedTemporaryFile') as mock_temp, \
         patch('instabids.tools.stt_tool.os.unlink'):
        
        # Set up the mock response with low confidence
        mock_transcribe.return_value = {
            "text": "Unclear audio transcription",
            "avg_logprob": -2.5,  # Low confidence (worse than threshold)
        }
        
        # Set up mock temp file
        mock_file = MagicMock()
        mock_temp.return_value.__enter__.return_value = mock_file
        
        # Call the function
        result = await speech_to_text(SAMPLE_AUDIO)
        
        # Verify the result is None due to low confidence
        assert result is None

@pytest.mark.asyncio
async def test_speech_to_text_error_handling():
    """Test error handling in speech-to-text processing."""
    # Mock the OpenAI API call to raise an exception
    with patch('instabids.tools.stt_tool.openai.Audio.atranscribe', new_callable=AsyncMock) as mock_transcribe, \
         patch('instabids.tools.stt_tool.tempfile.NamedTemporaryFile') as mock_temp:
        
        # Set up the mock to raise an exception
        mock_transcribe.side_effect = Exception("API error")
        
        # Set up mock temp file
        mock_file = MagicMock()
        mock_temp.return_value.__enter__.return_value = mock_file
        
        # Call the function and expect an exception
        with pytest.raises(Exception):
            await speech_to_text(SAMPLE_AUDIO)

@pytest.mark.asyncio
async def test_speech_to_text_threshold():
    """Test that the log probability threshold is appropriate."""
    # This test verifies that our threshold constant is set correctly
    assert LOGPROB_THRESH == -1.8, "Log probability threshold should be -1.8"
    
    # Mock the OpenAI API call
    with patch('instabids.tools.stt_tool.openai.Audio.atranscribe', new_callable=AsyncMock) as mock_transcribe, \
         patch('instabids.tools.stt_tool.tempfile.NamedTemporaryFile') as mock_temp, \
         patch('instabids.tools.stt_tool.os.unlink'):
        
        # Set up the mock response with exactly threshold confidence
        mock_transcribe.return_value = {
            "text": "Borderline confidence transcription",
            "avg_logprob": LOGPROB_THRESH,
        }
        
        # Set up mock temp file
        mock_file = MagicMock()
        mock_temp.return_value.__enter__.return_value = mock_file
        
        # Call the function
        result = await speech_to_text(SAMPLE_AUDIO)
        
        # Verify the result is None since it's exactly at threshold (not better than)
        assert result is None