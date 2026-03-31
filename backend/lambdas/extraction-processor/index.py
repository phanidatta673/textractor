import json
import os
import boto3
import io
import zipfile
from datetime import datetime
import time
from pypdf import PdfReader
import docx

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME', 'Extractions')

def handler(event, context):
    records = event.get('Records', [])
    
    for record in records:
        # Check if it's an S3 event or a manual invocation
        if 's3' in record:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
        else:
            # Handle manual payload from StartExtraction if structured differently
            # But we structured it like S3 in StartExtraction
            continue

        # URL decode key if necessary (S3 events often encode keys)
        from urllib.parse import unquote_plus
        key = unquote_plus(key)
        
        # Extract fileId from key: uploads/uuid.ext -> uuid
        file_id = key.split('/')[-1].split('.')[0] if '/' in key else key.split('.')[0]

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
    ttl = int(time.time()) + 600
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

    table.update_item(
        Key={'fileId': file_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attr_names,
        ExpressionAttributeValues=expression_attr_values
    )
