"""
Supabase tools for interacting with Supabase from agents.
"""
from typing import Dict, Any, List, Optional
import os
import logging
from supabase import create_client, Client

# Set up logging
logger = logging.getLogger(__name__)

class SupabaseTool:
    """
    Tool for interacting with Supabase from agents.
    Provides methods for common database operations.
    """
    
    def __init__(self):
        """Initialize the Supabase tool with client from environment variables."""
        try:
            # Use get() with default values for testing environments
            self.url = os.environ.get("SUPABASE_URL", "https://example.supabase.co")
            self.key = os.environ.get("SUPABASE_KEY", "dummy_key_for_testing")
            
            # Only create a real client if both values are properly set
            if self.url != "https://example.supabase.co" and self.key != "dummy_key_for_testing":
                self.client = create_client(self.url, self.key)
                logger.info("Initialized SupabaseTool with real client")
            else:
                logger.warning("Using mock Supabase client for testing (missing environment variables)")
                self.client = self._create_mock_client()
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = self._create_mock_client()
    
    def _create_mock_client(self) -> Any:
        """
        Create a mock client for testing environments.
        
        Returns:
            A simple object that mimics the Supabase client interface
        """
        class MockTable:
            def select(self, *args, **kwargs):
                return self
                
            def insert(self, *args, **kwargs):
                return self
                
            def update(self, *args, **kwargs):
                return self
                
            def delete(self, *args, **kwargs):
                return self
                
            def eq(self, *args, **kwargs):
                return self
                
            def gt(self, *args, **kwargs):
                return self
                
            def lt(self, *args, **kwargs):
                return self
                
            def execute(self):
                logger.warning("Mock Supabase client executed a query")
                return type('obj', (object,), {'data': []})
        
        class MockClient:
            def table(self, _):
                return MockTable()
        
        return MockClient()
    
    def query_table(self, table_name: str, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query a table with optional filters.
        
        Args:
            table_name: Name of the table to query
            query_params: Optional dictionary of query parameters
            
        Returns:
            List of records matching the query
        """
        try:
            query = self.client.table(table_name).select("*")
            
            # Apply filters if provided
            if query_params:
                for key, value in query_params.items():
                    if key == "eq":
                        for field, val in value.items():
                            query = query.eq(field, val)
                    elif key == "gt":
                        for field, val in value.items():
                            query = query.gt(field, val)
                    elif key == "lt":
                        for field, val in value.items():
                            query = query.lt(field, val)
                    # Add more filter types as needed
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Error querying table {table_name}: {e}")
            return []
    
    def insert_record(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a record into a table.
        
        Args:
            table_name: Name of the table
            record: Dictionary of field values to insert
            
        Returns:
            The inserted record
        """
        try:
            result = self.client.table(table_name).insert(record).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Error inserting into table {table_name}: {e}")
            return {}
    
    def update_record(self, table_name: str, record_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a record in a table.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record to update
            updates: Dictionary of field values to update
            
        Returns:
            The updated record
        """
        try:
            result = self.client.table(table_name).update(updates).eq("id", record_id).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Error updating record {record_id} in table {table_name}: {e}")
            return {}
    
    def delete_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """
        Delete a record from a table.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record to delete
            
        Returns:
            The deleted record
        """
        try:
            result = self.client.table(table_name).delete().eq("id", record_id).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Error deleting record {record_id} from table {table_name}: {e}")
            return {}

# Create a singleton instance for easy import
supabase_tool = SupabaseTool()