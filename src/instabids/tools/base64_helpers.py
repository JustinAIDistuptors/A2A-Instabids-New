'''
Base64 encoding/decoding utilities for working with images and other binary data.

Provides helper functions for converting between file paths, binary data, and base64 strings,
making it easier to work with images in APIs and storage.
'''
import base64
import os
from typing import Optional, Union, BinaryIO
from pathlib import Path

def encode_image_file(image_path: Union[str, Path]) -> str:
    '''
    Encode an image file to a base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string
        
    Raises:
        FileNotFoundError: If the image file does not exist
    '''
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def encode_image_data(image_data: bytes) -> str:
    '''
    Encode binary image data to a base64 string.
    
    Args:
        image_data: Binary image data
        
    Returns:
        Base64 encoded string
    '''
    return base64.b64encode(image_data).decode('utf-8')

def decode_base64(base64_string: str) -> bytes:
    '''
    Decode a base64 string to binary data.
    
    Args:
        base64_string: Base64 encoded string
        
    Returns:
        Binary data
    '''
    return base64.b64decode(base64_string)

def save_base64_to_file(base64_string: str, output_path: Union[str, Path], 
                       make_dirs: bool = True) -> Path:
    '''
    Save a base64 encoded string to a file.
    
    Args:
        base64_string: Base64 encoded string
        output_path: Path where the file should be saved
        make_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        Path object for the saved file
        
    Raises:
        ValueError: If the base64 string is invalid
        OSError: If the file cannot be written or directories created
    '''
    # Convert to Path object
    path = Path(output_path)
    
    # Create parent directories if they don't exist
    if make_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)
    
    # Decode and write the data
    data = decode_base64(base64_string)
    with open(path, "wb") as f:
        f.write(data)
        
    return path

def get_data_uri(base64_string: str, mime_type: str = "image/jpeg") -> str:
    '''
    Create a data URI from a base64 string.
    
    Args:
        base64_string: Base64 encoded string
        mime_type: MIME type for the data
        
    Returns:
        Data URI string
    '''
    return f"data:{mime_type};base64,{base64_string}"

def extract_from_data_uri(data_uri: str) -> tuple[str, str]:
    '''
    Extract the MIME type and base64 data from a data URI.
    
    Args:
        data_uri: Data URI string
        
    Returns:
        Tuple of (mime_type, base64_string)
        
    Raises:
        ValueError: If the data URI is invalid
    '''
    if not data_uri.startswith('data:'):
        raise ValueError("Invalid data URI format")
    
    # Split the data URI
    parts = data_uri.split(',', 1)
    if len(parts) != 2:
        raise ValueError("Invalid data URI format")
    
    # Get the MIME type and encoding
    header, base64_string = parts
    mime_parts = header.split(';')
    mime_type = mime_parts[0].replace('data:', '')
    
    return mime_type, base64_string

def get_temp_image_path(prefix: str = "instabids_", suffix: str = ".jpg", 
                       dir: Optional[Union[str, Path]] = None) -> Path:
    '''
    Generate a temporary file path for an image.
    
    Args:
        prefix: Prefix for the filename
        suffix: Suffix for the filename (file extension)
        dir: Directory to create the file in (defaults to system temp dir)
        
    Returns:
        Path object for the temporary file
    '''
    import tempfile
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=dir)
    os.close(fd)  # Close the file descriptor
    return Path(path)
