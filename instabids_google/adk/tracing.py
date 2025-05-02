"""Tracing utilities for ADK agents."""
from __future__ import annotations

import logging
import sys
from typing import Literal, Optional, Union

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def enable_tracing(
    output: Union[Literal["stdout"], str, None] = None,
    level: int = logging.INFO,
) -> None:
    """Enable tracing for ADK agents.
    
    Args:
        output: Where to send trace output. Can be "stdout" for console output,
            a file path string, or None to disable tracing.
        level: The logging level to use.
    """
    logger = logging.getLogger("instabids_google.adk")
    logger.setLevel(level)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    if output == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    elif output is not None:
        handler = logging.FileHandler(output)
    else:
        # No output specified, return without adding handlers
        return
    
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    logger.info("Tracing enabled for ADK agents")