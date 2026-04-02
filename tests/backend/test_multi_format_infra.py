import requests
import json
import time
import os
import zipfile
from pypdf import PdfWriter
from docx import Document
import io

API_BASE = "http://54.234.232.237/api"
SECRET_CODE = "super-secret-textractor-code"
BUCKET = "text-extractor-uploads-20260331222735145300000002"

def create_test_files():
    print("Creating test files...")
    
    # 1. PDF
    pdf_path = "test_sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    # 2. DOCX
    docx_path = "test_sample.docx"
    doc = Document()
    doc.add_paragraph("This is a test DOCX content.")
    doc.save(docx_path)

    # 3. ZIP
    zip_path = "test_sample.zip"
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr("inner_test.txt", "Content inside zip file.")
        z.write(docx_path)

    return [
        {"path": pdf_path, "type": "application/pdf"},
        {"path": docx_path, "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        {"path": zip_path, "type": "application/zip"}
    ]

def run_test(file_info):
    path = file_info['path']
    ctype = file_info['type']
    print(f"\nTesting file: {path} ({ctype})")
    
    headers = {"X-Secret-Code": SECRET_CODE}
    
    # 1. Get Presigned URL
    res = requests.post(f"{API_BASE}/presigned-url", json={
        "filename": path,
        "contentType": ctype
    }, headers=headers)
    res.raise_for_status()
    data = res.json()
    upload_url = data['uploadUrl']
    file_id = data['fileId']
    key = data['key']

    # 2. Upload to S3
    with open(path, "rb") as f:
        res = requests.put(upload_url, data=f, headers={"Content-Type": ctype})
    res.raise_for_status()

    # 3. Start Extraction
    res = requests.post(f"{API_BASE}/start", json={
        "fileId": file_id,
        "key": key,
        "bucket": BUCKET
    }, headers=headers)
    res.raise_for_status()

    # 4. Poll Status
    for _ in range(15):
        time.sleep(2)
        res = requests.get(f"{API_BASE}/status/{file_id}")
        status_data = res.json()
        print(f"  Status: {status_data['status']}")
        if status_data['status'] == 'COMPLETED':
            print(f"  Success! Length of content: {len(status_data.get('content', ''))}")
            return True
        if status_data['status'] == 'FAILED':
            print(f"  Failed: {status_data.get('error')}")
            return False
    
    print("  Timed out.")
    return False

if __name__ == "__main__":
    files = create_test_files()
    results = []
    try:
        for f in files:
            results.append(run_test(f))
    finally:
        for f in files:
            if os.path.exists(f['path']):
                os.remove(f['path'])
    
    if all(results):
        print("\nAll formats passed!")
    else:
        print("\nSome formats failed.")
