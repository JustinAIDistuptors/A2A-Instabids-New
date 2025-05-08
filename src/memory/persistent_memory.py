"""
Simplified PersistentMemory implementation for testing.
"""

import logging
from typing import Dict, Any, Optional
import datetime

from google.adk.memory import Memory

logger = logging.getLogger(__name__)


class PersistentMemory(Dict[str, Any]):
    """
    Simplified dictionary-based persistent memory for testing.
    """

    def __init__(self, project_id: Optional[str] = None, initial_state: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.project_id = project_id
        if initial_state:
            self.update(initial_state)
