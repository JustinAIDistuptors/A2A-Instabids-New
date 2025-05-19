from mem0 import MemoryClient

# WARNING: Hardcoding API keys is generally not recommended for production or shared code.
# This is for initial testing purposes only as per user request.
API_KEY = "m0-bJd1nMyIB0gGuGP0TjOrFLyy5XKsbPWsrbEp0vrR"

# Initialize the client
print("Initializing Mem0 Client...")
try:
    client = MemoryClient(api_key=API_KEY)
    print("Mem0 Client initialized successfully.")
except Exception as e:
    print(f"Error initializing client: {e}")
    client = None

if client:
    USER_ID = "test_user_123"
    TEST_MEMORY_CONTENT_ADD = "The user enjoys learning about new AI technologies."
    TEST_MEMORY_ASSISTANT_RESPONSE = "Noted! User is interested in AI tech."
    TEST_QUERY = "What is the user interested in?"

    # Add a memory
    print(f"\nAdding memory for user: {USER_ID}")
    try:
        client.add(
            [
                {"role": "user", "content": TEST_MEMORY_CONTENT_ADD},
                {"role": "assistant", "content": TEST_MEMORY_ASSISTANT_RESPONSE}
            ],
            user_id=USER_ID
        )
        print("Memory added successfully.")
    except Exception as e:
        print(f"Error adding memory: {e}")

    # Search for the memory
    print(f"\nSearching for memory with query: '{TEST_QUERY}' for user: {USER_ID}")
    try:
        memories = client.search(query=TEST_QUERY, user_id=USER_ID)
        print("Search complete.")
        if memories:
            print("Retrieved memories:")
            for mem in memories:
                # The structure of 'mem' might vary, printing its raw form for now
                # Based on website example, it might be a direct string or a list of dicts
                print(mem)
        else:
            print("No memories found for this query.")
    except Exception as e:
        print(f"Error searching memory: {e}")
else:
    print("Skipping memory operations as client initialization failed.")

print("\nTest script finished.")
