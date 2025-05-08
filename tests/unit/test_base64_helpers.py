'''
Unit tests for the base64_helpers module.

Tests the functionality of the encoding, decoding, and file operations
in the base64_helpers module.
'''
import pytest
import os
import tempfile
from pathlib import Path
import base64

from instabids.tools.base64_helpers import (
    encode_image_file, 
    encode_image_data, 
    decode_base64, 
    save_base64_to_file,
    get_data_uri,
    extract_from_data_uri,
    get_temp_image_path
)

# Sample test data
SAMPLE_TEXT = "Hello, world!"
SAMPLE_BASE64 = "SGVsbG8sIHdvcmxkIQ=="  # base64 encoded version of "Hello, world!"
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_image_file(temp_dir):
    """Create a sample image file for testing."""
    image_path = temp_dir / "test_image.jpg"
    image_data = base64.b64decode(SAMPLE_IMAGE_BASE64)
    with open(image_path, "wb") as f:
        f.write(image_data)
    return image_path

def test_encode_image_file(sample_image_file):
    """Test encoding an image file to base64."""
    result = encode_image_file(sample_image_file)
    assert isinstance(result, str)
    # Check if the result is valid base64
    try:
        base64.b64decode(result)
        valid_base64 = True
    except Exception:
        valid_base64 = False
    assert valid_base64

def test_encode_image_file_not_found():
    """Test that encode_image_file raises FileNotFoundError for non-existent files."""
    with pytest.raises(FileNotFoundError):
        encode_image_file("non_existent_file.jpg")

def test_encode_image_data():
    """Test encoding binary data to base64."""
    binary_data = SAMPLE_TEXT.encode('utf-8')
    result = encode_image_data(binary_data)
    assert result == SAMPLE_BASE64

def test_decode_base64():
    """Test decoding base64 to binary data."""
    result = decode_base64(SAMPLE_BASE64)
    assert result == SAMPLE_TEXT.encode('utf-8')
    
    # Also test with image data
    image_data = decode_base64(SAMPLE_IMAGE_BASE64)
    assert isinstance(image_data, bytes)
    assert len(image_data) > 0

def test_save_base64_to_file(temp_dir):
    """Test saving base64 data to a file."""
    output_path = temp_dir / "output.txt"
    result = save_base64_to_file(SAMPLE_BASE64, output_path)
    
    # Check the result is a Path object
    assert isinstance(result, Path)
    assert result == output_path
    
    # Check the file exists and has the correct content
    assert output_path.exists()
    with open(output_path, "rb") as f:
        content = f.read()
    assert content == SAMPLE_TEXT.encode('utf-8')

def test_save_base64_to_file_creates_directories(temp_dir):
    """Test that save_base64_to_file creates parent directories if they don't exist."""
    output_path = temp_dir / "subdir" / "nested" / "output.txt"
    result = save_base64_to_file(SAMPLE_BASE64, output_path)
    
    # Check the file exists and has the correct content
    assert output_path.exists()
    with open(output_path, "rb") as f:
        content = f.read()
    assert content == SAMPLE_TEXT.encode('utf-8')

def test_get_data_uri():
    """Test creating a data URI from a base64 string."""
    result = get_data_uri(SAMPLE_BASE64)
    assert result == f"data:image/jpeg;base64,{SAMPLE_BASE64}"
    
    # Test with a custom MIME type
    result = get_data_uri(SAMPLE_BASE64, mime_type="text/plain")
    assert result == f"data:text/plain;base64,{SAMPLE_BASE64}"

def test_extract_from_data_uri():
    """Test extracting the MIME type and base64 data from a data URI."""
    data_uri = f"data:image/png;base64,{SAMPLE_BASE64}"
    mime_type, base64_string = extract_from_data_uri(data_uri)
    
    assert mime_type == "image/png"
    assert base64_string == SAMPLE_BASE64

def test_extract_from_data_uri_invalid_format():
    """Test that extract_from_data_uri raises ValueError for invalid data URIs."""
    with pytest.raises(ValueError):
        extract_from_data_uri("invalid_data_uri")
    
    with pytest.raises(ValueError):
        extract_from_data_uri("data:image/png")

def test_get_temp_image_path():
    """Test generating a temporary file path for an image."""
    result = get_temp_image_path()
    
    # Check the result is a Path object
    assert isinstance(result, Path)
    
    # Check the path has the expected format
    assert result.name.startswith("instabids_")
    assert result.name.endswith(".jpg")
    
    # Check the file exists (though it should be empty)
    assert result.exists()
    
    # Clean up
    os.unlink(result)