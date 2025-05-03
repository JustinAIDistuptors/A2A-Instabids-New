"""
Logs every prompt/response pair to the messages table. Usable as
`@memory_logger` decorator around LlmAgent.chat.  Inspired by OpenAI function
call logging patterns. (No external deps.)
"""
from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TypeVar, cast
from instabids.data.messages_repo import insert_message

# Type variables for better type hinting
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

def memory_logger(agent_name: str) -> Callable[[F], F]:
    """
    Decorator that logs agent conversations to the messages table.
    
    Args:
        agent_name: Name of the agent for context (can be used for filtering)
        
    Returns:
        Decorated function that logs messages before and after execution
    """
    def decorator(chat_fn: F) -> F:
        @wraps(chat_fn)
        async def wrapper(self, msg: Any, *args: Any, **kw: Any) -> Any:
            # Extract project_id from kwargs or message metadata
            project_id = kw.get("project_id") or msg.metadata.get("project_id")
            
            if not project_id:
                # Skip logging if no project_id is available
                return await chat_fn(self, msg, *args, **kw)
            
            # Log homeowner message
            insert_message(
                project_id=project_id,
                role="homeowner",
                content=msg.content,
            )
            
            # Execute the original function
            res = await chat_fn(self, msg, *args, **kw)
            
            # Log agent response
            insert_message(
                project_id=project_id,
                role="agent",
                content=res.content,
            )
            
            return res
        
        return cast(F, wrapper)
    
    return decorator