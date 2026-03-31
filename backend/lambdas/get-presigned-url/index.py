import json
import os
import uuid
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME')

def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        content_type = body.get('contentType')

        if not filename or not content_type:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing filename or contentType'})
            }

        file_id = str(uuid.uuid4())
        extension = filename.split('.')[-1] if '.' in filename else ''
        key = f"uploads/{file_id}.{extension}" if extension else f"uploads/{file_id}"

        try:
            upload_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': key,
                    'ContentType': content_type
                },
                ExpiresIn=3600
            )
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'content-type',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'uploadUrl': upload_url,
                'fileId': file_id,
                'key': key
            })
        }
    except Exception as e:
        print(f"Exception: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
