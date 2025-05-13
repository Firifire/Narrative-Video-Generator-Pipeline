import requests
LM_STUDIO_SERVER_URL = "http://localhost:1234/v1" # Or your actual base URL
try:
    response = requests.get(f"{LM_STUDIO_SERVER_URL}/models") # A different, simpler endpoint
    response.raise_for_status()
    print("Successfully connected and got models:", response.json())
except requests.exceptions.RequestException as e:
    print(f"Failed to connect to LM Studio: {e}")