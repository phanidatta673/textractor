import json
import os
import boto3
from datetime import datetime
import time

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

TABLE_NAME = os.environ.get('TABLE_NAME')
PROCESSOR_LAMBDA = os.environ.get('PROCESSOR_LAMBDA')

def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        file_id = body.get('fileId')
        key = body.get('key')
        bucket = body.get('bucket')

        if not file_id or not key or not bucket:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing fileId, key, or bucket'})
            }

        # 1. Initial status update to DynamoDB
        ttl = int(time.time()) + 600  # 10 minutes
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'fileId': file_id,
                'status': 'PENDING',
                'updatedAt': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
        )

        # 2. Asynchronously invoke ExtractionProcessor
        payload = {
            'Records': [{
                's3': {
                    'bucket': {'name': bucket},
                    'object': {'key': key}
                }
            }]
        }

        lambda_client.invoke(
            FunctionName=PROCESSOR_LAMBDA,
            InvocationType='Event',
            Payload=json.dumps(payload)
        )

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'content-type',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({'message': 'Extraction started', 'fileId': file_id})
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
