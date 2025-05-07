"""
Mock Supabase client for testing.

This module provides a mock Supabase client for testing that returns
predefined responses and doesn't actually connect to a real Supabase instance.
"""

from unittest.mock import MagicMock

class MockSupabaseResponse:
    """Mock response from Supabase."""
    
    def __init__(self, data=None, error=None):
        """Initialize the mock response."""
        self.data = data or []
        self.error = error


class MockSupabaseChain:
    """Mock chain of Supabase methods."""
    
    def __init__(self, data=None):
        """Initialize the mock chain."""
        self.data = data or [{"id": "mock-id"}]
    
    def execute(self):
        """Execute the query and return a response."""
        return MockSupabaseResponse(data=self.data)
    
    # Support method chaining
    def eq(self, *args, **kwargs):
        """Equal filter."""
        return self
    
    def neq(self, *args, **kwargs):
        """Not equal filter."""
        return self
    
    def gt(self, *args, **kwargs):
        """Greater than filter."""
        return self
    
    def gte(self, *args, **kwargs):
        """Greater than or equal filter."""
        return self
    
    def lt(self, *args, **kwargs):
        """Less than filter."""
        return self
    
    def lte(self, *args, **kwargs):
        """Less than or equal filter."""
        return self
    
    def in_(self, *args, **kwargs):
        """In filter."""
        return self
    
    def is_(self, *args, **kwargs):
        """Is filter."""
        return self
    
    def like(self, *args, **kwargs):
        """Like filter."""
        return self
    
    def ilike(self, *args, **kwargs):
        """Case-insensitive like filter."""
        return self
    
    def limit(self, *args, **kwargs):
        """Limit results."""
        return self


class MockSupabaseTable:
    """Mock Supabase table."""
    
    def __init__(self, name, data=None):
        """Initialize the mock table."""
        self.name = name
        self.data = data or [{"id": f"mock-{name}-id"}]
    
    def select(self, *args, **kwargs):
        """Select columns."""
        return MockSupabaseChain(data=self.data)
    
    def insert(self, data, *args, **kwargs):
        """Insert data."""
        if isinstance(data, list):
            result = []
            for item in data:
                item_copy = item.copy()
                if "id" not in item_copy:
                    item_copy["id"] = f"mock-{self.name}-id"
                result.append(item_copy)
        else:
            result = [data.copy()]
            if "id" not in result[0]:
                result[0]["id"] = f"mock-{self.name}-id"
        
        return MockSupabaseChain(data=result)
    
    def update(self, data, *args, **kwargs):
        """Update data."""
        return MockSupabaseChain(data=self.data)
    
    def delete(self, *args, **kwargs):
        """Delete data."""
        return MockSupabaseChain(data=[])
    
    def upsert(self, data, *args, **kwargs):
        """Upsert data."""
        return self.insert(data)


class MockSupabaseClient:
    """Mock Supabase client."""
    
    def __init__(self):
        """Initialize the mock client."""
        pass
    
    def table(self, name):
        """Get a table."""
        return MockSupabaseTable(name)
    
    def rpc(self, name, *args, **kwargs):
        """Call a stored procedure."""
        if name == "pgmeta_query":
            # Mock schema information
            query = kwargs.get("query", "")
            if "tables" in query:
                return MockSupabaseChain(data=[
                    {"table_name": "users"},
                    {"table_name": "projects"},
                    {"table_name": "bid_cards"},
                    {"table_name": "bids"},
                    {"table_name": "contractor_matches"},
                    {"table_name": "user_memories"},
                    {"table_name": "user_memory_interactions"}
                ])
            elif "columns" in query:
                return MockSupabaseChain(data=[
                    {"column_name": "id"},
                    {"column_name": "bid_card_id"},
                    {"column_name": "details"},
                    {"column_name": "homeowner_id"}
                ])
        
        return MockSupabaseChain()
    
    def auth(self):
        """Get the auth client."""
        auth_client = MagicMock()
        return auth_client


def create_mock_supabase_client(*args, **kwargs):
    """Create a mock Supabase client."""
    return MockSupabaseClient()
