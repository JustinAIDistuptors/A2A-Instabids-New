"""
Middleware components for agent functionality.

This package contains middleware that can be applied to agents to add
functionality such as logging, caching, and other cross-cutting concerns.
"""

from instabids.middleware.memory_logger import memory_logger

__all__ = ["memory_logger"]