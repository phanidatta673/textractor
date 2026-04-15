import hmac
import hashlib
from backend.monolith.utils import verify_github_signature

def test_verify_github_signature_valid():
    secret = "test-secret"
    payload = b'{"action": "opened"}'
    signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_github_signature(payload, signature, secret) is True

def test_verify_github_signature_invalid():
    assert verify_github_signature(b"{}", "sha256=invalid", "secret") is False
