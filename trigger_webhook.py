import hmac
import hashlib
import json
import requests

secret = "GHN0Himetsu*#$#$"
payload = {
    "action": "opened",
    "issue": {
        "number": 12,
        "title": "Change the 'Submit All' button text to 'Extract Now'",
        "body": "Change the 'Submit All' button text to 'Extract Now'"
    }
}

payload_body = json.dumps(payload).encode()
signature = "sha256=" + hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()

url = "http://98.88.82.184/api/webhooks/github"
headers = {
    "X-Hub-Signature-256": signature,
    "X-GitHub-Event": "issues",
    "Content-Type": "application/json"
}

response = requests.post(url, data=payload_body, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
