import requests
import json

url = "http://localhost:8000/api/v1/experiences/search"
headers = {"Content-Type": "application/json"}
data = {"query": "concurrency"}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
