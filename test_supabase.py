import os
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

from src.instabids.tools.supabase import supabase_client

# Test Supabase connection
def test_supabase_connection():
    print("Testing Supabase connection...")
    try:
        # Test Supabase client connection
        client = supabase_client()
        result = client.table("users").select("*").execute()
        print("Supabase client type:", type(client))
        print("Connection successful!")
        print("First 2 rows:", result.data[:2])
        return True
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_supabase_connection()
