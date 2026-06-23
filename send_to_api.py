import requests

API_URL = "http://127.0.0.1:8000/api/event"

def send_to_api(payload):
    try:
        requests.post(API_URL, json=payload, timeout=3)
    except Exception as e:
        print("API error:", e)