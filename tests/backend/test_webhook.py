import os
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"
os.environ["BUCKET_NAME"] = "test-bucket"
os.environ["TABLE_NAME"] = "Extractions"

import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from backend.monolith.main import app
from backend.monolith.utils import verify_github_signature

client = TestClient(app)

def test_verify_github_signature_valid():
    secret = "test-secret"
    payload = b'{"action": "opened"}'
    signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_github_signature(payload, signature, secret) is True

def test_verify_github_signature_invalid():
    assert verify_github_signature(b"{}", "sha256=invalid", "secret") is False

def test_github_webhook_endpoint_no_signature():
    response = client.post("/api/webhooks/github", json={"action": "opened"})
    assert response.status_code == 403

def test_github_webhook_endpoint_valid_issue(monkeypatch):
    import backend.monolith.main as main_module
    
    # Mock run_agent_orchestrator
    called_with = None
    async def mock_run_agent_orchestrator(issue_data):
        nonlocal called_with
        called_with = issue_data
    
    monkeypatch.setattr(main_module, "run_agent_orchestrator", mock_run_agent_orchestrator)
    monkeypatch.setattr(main_module, "GITHUB_WEBHOOK_SECRET", "test-secret")
    
    issue_payload = {"number": 123}
    payload = json.dumps({"action": "opened", "issue": issue_payload}).encode()
    
    import hmac, hashlib
    sig = "sha256=" + hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
    
    response = client.post(
        "/api/webhooks/github",
        content=payload,
        headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": "issues"}
    )
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    
    # Check if background task was added. 
    # Since it's a background task, we need to wait for it or use a mock that tracks it.
    # Actually, in FastAPI TestClient, background tasks are executed after the response.
    assert called_with == issue_payload
