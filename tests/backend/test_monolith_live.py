import requests
import time
import os

API_BASE = "http://98.89.24.130"
SECRET_CODE = "super-secret-textractor-code"

def test_live_health():
    print("Testing /health...")
    res = requests.get(f"{API_BASE}/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}
    print("  Health check passed.")

def test_live_dashboard():
    print("Testing /html...")
    res = requests.get(f"{API_BASE}/html")
    assert res.status_code == 200
    assert "<title>Text Extractor Dashboard</title>" in res.text
    print("  Dashboard check passed.")

def test_live_extraction():
    print("Testing /api/process...")
    test_content = "This is a live test for monolith extraction."
    files = {'file': ('test_live.txt', test_content, 'text/plain')}
    headers = {'X-Secret-Code': SECRET_CODE}
    
    res = requests.post(f"{API_BASE}/api/process", files=files, headers=headers)
    if res.status_code != 200:
        print(f"  Error: {res.status_code} - {res.text}")
    assert res.status_code == 200
    
    file_id = res.json()['fileId']
    print(f"  Extraction started, fileId: {file_id}")
    
    # Poll status
    print("  Polling status...")
    for _ in range(15):
        time.sleep(2)
        res = requests.get(f"{API_BASE}/api/status/{file_id}")
        assert res.status_code == 200
        data = res.json()
        print(f"    Status: {data['status']}")
        if data['status'] == 'COMPLETED':
            print(f"    Success! Extracted content matches: {data['content'] == test_content}")
            assert data['content'].strip() == test_content.strip()
            return
        if data['status'] == 'FAILED':
            print(f"    Failed: {data.get('error')}")
            assert False
            
    print("  Timed out waiting for extraction.")
    assert False

if __name__ == "__main__":
    try:
        test_live_health()
        test_live_dashboard()
        test_live_extraction()
        print("\nAll live tests passed!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        exit(1)
