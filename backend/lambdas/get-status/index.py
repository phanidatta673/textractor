import json
import os
import boto3
from decimal import Decimal

# Helper to handle DynamoDB decimals
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')

def handler(event, context):
    try:
        path_parameters = event.get('pathParameters')
        file_id = path_parameters.get('fileId') if path_parameters else None

        if not file_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing fileId'})
            }

        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'fileId': file_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Record not found'})
            }

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'content-type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(item, cls=DecimalEncoder)
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
