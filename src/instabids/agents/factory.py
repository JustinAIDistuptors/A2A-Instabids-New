"""Agent singleton factory & cache."""
from google.adk import LlmAgent, enable_tracing
from instabids.tools import supabase_tools
from instabids.agents.contractor import create_contractor_agent
from memory.persistent_memory import PersistentMemory
from .homeowner_agent import HomeownerAgent
from .bid_card_agent import BidCardAgent

enable_tracing("stdout")

_mem_store = PersistentMemory()
_homeowner_instance: HomeownerAgent | None = None
_bidcard_instance: BidCardAgent | None = None
_contractor = None


def get_homeowner_agent(memory: PersistentMemory | None = None) -> HomeownerAgent:  # noqa: D401
    """Return singleton HomeownerAgent."""
    global _homeowner_instance
    if _homeowner_instance is None:
        _homeowner_instance = HomeownerAgent(memory or _mem_store)
    return _homeowner_instance


def get_contractor_agent(memory: PersistentMemory = None) -> LlmAgent:
    """Returns a contractor agent with memory injection if provided."""
    global _contractor
    if _contractor is None or memory is not None:
        _contractor = create_contractor_agent(memory)
    return _contractor


def get_bidcard_agent() -> BidCardAgent:
    """Return singleton BidCardAgent."""
    global _bidcard_instance
    if _bidcard_instance is None:
        _bidcard_instance = BidCardAgent()
    return _bidcard_instance
