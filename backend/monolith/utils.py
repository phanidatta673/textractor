import hmac
import hashlib

def verify_github_signature(payload_body, signature_header, secret):
    if not signature_header or not secret:
        return False
    hash_object = hmac.new(secret.encode(), payload_body, hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)
