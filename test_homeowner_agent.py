# test_homeowner_agent.py
import requests
import json

API_URL = "http://localhost:8001/a2a/v1/tasks"
HEADERS = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": "sha256=dummy_signature_value"
}
PAYLOAD = {
    "homeowner_id": "user_test_mvp_001",
    "conversation_history": [
        {"role": "user", "content": "Hello, I have a plumbing issue."}
    ],
    "message": "My kitchen sink is leaking badly under the cabinet.",
    "project_type_preference": "repair"
}

try:
    print(f"Sending POST request to {API_URL}...")
    response = requests.post(API_URL, headers=HEADERS, data=json.dumps(PAYLOAD), timeout=30)
    response.raise_for_status() 
    
    print(f"Response Status Code: {response.status_code}")
    response_data = response.json()
    print(f"Response JSON: {json.dumps(response_data, indent=2)}")
    
    if "task_id" in response_data:
        print(f"\n--- Successfully received task_id: {response_data['task_id']} ---")
    else:
        print("\n--- task_id not found in response. ---")
        
except requests.exceptions.HTTPError as http_err:
    print(f"\nHTTP error occurred: {http_err}")
    print(f"Response content: {response.content.decode() if response.content else 'No content'}")
except requests.exceptions.ConnectionError as conn_err:
    print(f"\nConnection error occurred: {conn_err}")
    print("Is the Uvicorn server (src.instabids.app:app) running on http://localhost:8001?")
except requests.exceptions.Timeout:
    print("\nThe request timed out.")
except requests.exceptions.RequestException as req_err:
    print(f"\nAn error occurred: {req_err}")
