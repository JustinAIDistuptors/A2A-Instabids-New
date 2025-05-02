"""Agent singleton factory & cache."""
from memory.persistent_memory import PersistentMemory
from instabids.agents.homeowner_agent import HomeownerAgent

_homeowner_singleton: HomeownerAgent | None = None

def get_homeowner_agent(memory: PersistentMemory | None = None) -> HomeownerAgent:
    global _homeowner_singleton
    if _homeowner_singleton is None:
        _homeowner_singleton = HomeownerAgent(memory=memory or PersistentMemory())
    return _homeowner_singleton