import hmac
import hashlib
import os
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
    monkeypatch.setattr(main_module, "GITHUB_WEBHOOK_SECRET", "test-secret")
    payload = b'{"action": "opened", "issue": {"number": 123}}'
    import hmac, hashlib
    sig = "sha256=" + hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
    
    response = client.post(
        "/api/webhooks/github",
        content=payload,
        headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": "issues"}
    )
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
