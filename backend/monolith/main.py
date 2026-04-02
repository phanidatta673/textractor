from fastapi import FastAPI, Header, HTTPException, Depends, BackgroundTasks, Body, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import uuid
import boto3
import io
import zipfile
import time
import json
import argparse
import sys
import re
import urllib.request
from datetime import datetime
from pypdf import PdfReader
import docx
from decimal import Decimal
from botocore.exceptions import ClientError
from urllib.parse import unquote_plus

app = FastAPI(title="Textractor Monolith")

# Configuration
BUCKET_NAME = os.environ.get('BUCKET_NAME')
TABLE_NAME = os.environ.get('TABLE_NAME', 'Extractions')
SECRET_CODE = os.environ.get('SECRET_CODE', 'dev-secret') # Default for dev

# AWS Clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Helper to handle DynamoDB decimals
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

async def verify_secret(x_secret_code: str = Header(None)):
    if x_secret_code != SECRET_CODE:
        raise HTTPException(status_code=403, detail="Invalid secret code")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extraction Logic
def extract_text(content, extension):
    if extension == 'pdf':
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    elif extension == 'docx':
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs])
    elif extension == 'txt':
        return content.decode('utf-8')
    elif extension == 'zip':
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            combined_text = ""
            for filename in z.namelist():
                if filename.endswith('/'): continue # Skip directories
                file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
                try:
                    with z.open(filename) as f:
                        data = f.read()
                        text = extract_text(data, file_ext)
                        combined_text += f"\n--- File: {filename} ---\n{text}\n"
                except Exception as e:
                    print(f"Skipping file {filename} in zip: {e}")
            return combined_text
    else:
        raise ValueError(f"Unsupported file type: {extension}")

def update_status(file_id, status, content=None, error=None):
    ttl = int(time.time()) + 3600 # 1 hour TTL for monolith
    table = dynamodb.Table(TABLE_NAME)
    
    update_expression = "SET #s = :s, #t = :t, #ttl = :ttl"
    expression_attr_names = {
        "#s": "status",
        "#t": "updatedAt",
        "#ttl": "ttl"
    }
    expression_attr_values = {
        ":s": status,
        ":t": datetime.utcnow().isoformat(),
        ":ttl": ttl
    }

    if content is not None:
        update_expression += ", #c = :c"
        expression_attr_names["#c"] = "content"
        expression_attr_values[":c"] = content
    
    if error is not None:
        update_expression += ", #e = :e"
        expression_attr_names["#e"] = "error"
        expression_attr_values[":e"] = error

    try:
        table.update_item(
            Key={'fileId': file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values
        )
    except Exception as e:
        print(f"Error updating DynamoDB: {e}")

async def process_extraction(bucket: str, key: str, file_id: str):
    # Ported from ExtractionProcessor
    try:
        update_status(file_id, 'PROCESSING')

        # Download file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read()

        extension = key.split('.')[-1].lower() if '.' in key else ''
        extracted_text = extract_text(file_content, extension)

        update_status(file_id, 'COMPLETED', content=extracted_text)

    except Exception as e:
        print(f"Extraction error for {file_id}: {e}")
        update_status(file_id, 'FAILED', error=str(e))

def process_github_issue(issue_id):
    repo = os.environ.get('GITHUB_REPOSITORY')
    token = os.environ.get('GITHUB_TOKEN')
    
    if not repo or not token:
        print("Error: GITHUB_REPOSITORY and GITHUB_TOKEN environment variables must be set.")
        return

    api_url = f"https://api.github.com/repos/{repo}/issues/{issue_id}"
    print(f"Fetching issue {issue_id} from {repo}...")

    # Fetch issue
    req = urllib.request.Request(api_url)
    req.add_header('Authorization', f'token {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'Textractor-CLI')
    
    try:
        with urllib.request.urlopen(req) as response:
            issue_data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching issue: {e}")
        return

    body = issue_data.get('body', '') or ""
    
    # Find links ending in supported extensions
    links = re.findall(r'https?://[^\s\)]+\.(?:pdf|docx|txt|zip)', body, re.IGNORECASE)
    links = list(set(links)) # Unique links
    
    results = []
    if not links:
        print("No supported attachments found in issue body.")
    
    for link in links:
        print(f"Processing: {link}")
        ext = link.split('.')[-1].lower()
        try:
            att_req = urllib.request.Request(link)
            if "github.com" in link:
                att_req.add_header('Authorization', f'token {token}')
            att_req.add_header('User-Agent', 'Textractor-CLI')
            
            with urllib.request.urlopen(att_req) as att_res:
                content = att_res.read()
                text = extract_text(content, ext)
                results.append(f"### Results for {os.path.basename(link)}\n\n```\n{text[:2000]}{'...' if len(text) > 2000 else ''}\n```")
        except Exception as e:
            print(f"Error processing {link}: {e}")
            results.append(f"### Error for {os.path.basename(link)}\n\n{str(e)}")

    if not results:
        comment_body = "CLI Mode: No supported attachments (PDF, DOCX, TXT, ZIP) found in the issue body."
    else:
        comment_body = "## Textractor Extraction Results\n\n" + "\n\n---\n\n".join(results)

    # Post comment
    comment_url = f"{api_url}/comments"
    data = json.dumps({"body": comment_body}).encode('utf-8')
    comment_req = urllib.request.Request(comment_url, data=data, method='POST')
    comment_req.add_header('Authorization', f'token {token}')
    comment_req.add_header('Accept', 'application/vnd.github.v3+json')
    comment_req.add_header('User-Agent', 'Textractor-CLI')
    comment_req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(comment_req) as response:
            print(f"Successfully posted comment to GitHub issue {issue_id}.")
    except Exception as e:
        print(f"Error posting comment: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/process", dependencies=[Depends(verify_secret)])
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    file_id = str(uuid.uuid4())
    filename = file.filename
    extension = filename.split('.')[-1] if '.' in filename else ''
    key = f"uploads/{file_id}.{extension}" if extension else f"uploads/{file_id}"
    
    # Read file content
    content = await file.read()
    
    # Upload to S3
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=file.content_type
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")

    # Initial status update in DynamoDB
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'fileId': file_id,
                'status': 'PENDING',
                'updatedAt': datetime.utcnow().isoformat(),
                'ttl': int(time.time()) + 3600,
                'filename': filename
            }
        )
    except Exception as e:
        print(f"Error putting initial item: {e}")
        # Even if DynamoDB fails, we've uploaded to S3. 
        # But for monolith consistency we might want to fail here.
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")

    # Add background task
    background_tasks.add_task(process_extraction, BUCKET_NAME, key, file_id)

    return {'message': 'Extraction started', 'fileId': file_id}

@app.get("/api/status/{file_id}")
async def get_status(file_id: str):

    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'fileId': file_id})
        item = response.get('Item')

        if not item:
            raise HTTPException(status_code=404, detail="Record not found")

        # Use DecimalEncoder for JSON serialization if needed, 
        # but FastAPI handles most types including Decimal sometimes, 
        # actually it might need custom encoder.
        # Let's return it as dict, FastAPI will serialize it.
        # To be safe with Decimal:
        return json.loads(json.dumps(item, cls=DecimalEncoder))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/html", response_class=HTMLResponse)
async def get_html():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    with open(os.path.join(static_dir, "index.html"), "r") as f:
        return f.read()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Textractor Monolith CLI")
    parser.add_argument("--process-issue", type=str, help="GitHub Issue ID to process")
    args = parser.parse_args()

    if args.process_issue:
        process_github_issue(args.process_issue)
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
