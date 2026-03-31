import requests
import json
import time

API_BASE = "https://w8cw1eshvc.execute-api.us-east-1.amazonaws.com"
TEST_FILE = "test_real_infra.txt"
TEST_CONTENT = "This is a test file for real infrastructure verification."

def test_real_infra():
    # 1. Get Presigned URL
    print("Step 1: Requesting presigned URL...")
    res = requests.post(f"{API_BASE}/presigned-url", json={
        "filename": TEST_FILE,
        "contentType": "text/plain"
    })
    res.raise_for_status()
    data = res.json()
    upload_url = data['uploadUrl']
    file_id = data['fileId']
    key = data['key']
    print(f"  Got fileId: {file_id}")

    # 2. Upload to S3
    print("Step 2: Uploading file to S3...")
    res = requests.put(upload_url, data=TEST_CONTENT, headers={"Content-Type": "text/plain"})
    res.raise_for_status()
    print("  Upload successful.")

    # 3. Start Extraction
    print("Step 3: Starting extraction...")
    # Note: bucket name is needed here. I'll get it from terraform outputs if possible, 
    # but I'll use the one from the generalist's response first.
    bucket = "text-extractor-uploads-20260331222735145300000002"
    res = requests.post(f"{API_BASE}/start", json={
        "fileId": file_id,
        "key": key,
        "bucket": bucket
    })
    res.raise_for_status()
    print("  Extraction started.")

    # 4. Poll Status
    print("Step 4: Polling status...")
    for _ in range(10):
        time.sleep(2)
        res = requests.get(f"{API_BASE}/status/{file_id}")
        res.raise_for_status()
        status_data = res.json()
        print(f"  Status: {status_data['status']}")
        if status_data['status'] == 'COMPLETED':
            print(f"  Success! Extracted content: {status_data['content']}")
            return
        if status_data['status'] == 'FAILED':
            print(f"  Failed: {status_data.get('error')}")
            return
    
    print("  Timed out waiting for extraction.")

if __name__ == "__main__":
    with open(TEST_FILE, "w") as f:
        f.write(TEST_CONTENT)
    try:
        test_real_infra()
    finally:
        import os
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
