import unittest
from unittest.mock import MagicMock, patch
import json
import os
import io
import sys
import importlib.util
import zipfile

# Mocking environment variables for tests
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['BUCKET_NAME'] = 'test-bucket'
os.environ['TABLE_NAME'] = 'Extractions'
os.environ['PROCESSOR_LAMBDA'] = 'ExtractionProcessor'

project_root = os.getcwd()

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, "index.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# Load each lambda as a unique module for testing
get_presigned_url_mod = load_module("get_presigned_url", os.path.join(project_root, 'backend/lambdas/get-presigned-url'))
start_extraction_mod = load_module("start_extraction", os.path.join(project_root, 'backend/lambdas/start-extraction'))
extraction_processor_mod = load_module("extraction_processor", os.path.join(project_root, 'backend/lambdas/extraction-processor'))
get_status_mod = load_module("get_status", os.path.join(project_root, 'backend/lambdas/get-status'))

class TestBackendExtractionFlow(unittest.TestCase):
    """
    Automated Backend Tests for TextExtractor Python Rewrite.
    Verifies the end-to-end integration of all Lambda functions.
    """

    def setUp(self):
        self.file_id = "test-uuid"
        self.key = "uploads/test-uuid.txt"
        self.bucket = "test-bucket"

    def test_01_get_presigned_url_flow(self):
        """Test Step 1: Requesting an S3 presigned URL for upload."""
        with patch('get_presigned_url.s3_client') as mock_s3:
            mock_s3.generate_presigned_url.return_value = "https://mock-url.com"
            event = {
                'body': json.dumps({
                    'filename': 'test.txt',
                    'contentType': 'text/plain'
                })
            }
            response = get_presigned_url_mod.handler(event, None)
            self.assertEqual(response['statusCode'], 200)
            
            body = json.loads(response['body'])
            self.assertIn('fileId', body)
            self.assertEqual(body['uploadUrl'], "https://mock-url.com")

    def test_02_start_extraction_flow(self):
        """Test Step 2: Starting the extraction process after S3 upload."""
        with patch('start_extraction.dynamodb') as mock_dynamo_res, \
             patch('start_extraction.lambda_client') as mock_lambda_client:
            
            mock_table = MagicMock()
            mock_dynamo_res.Table.return_value = mock_table
            
            start_event = {
                'body': json.dumps({
                    'fileId': self.file_id,
                    'key': self.key,
                    'bucket': self.bucket
                })
            }
            
            response = start_extraction_mod.handler(start_event, None)
            self.assertEqual(response['statusCode'], 200)
            mock_table.put_item.assert_called()
            mock_lambda_client.invoke.assert_called()

    def test_03_extraction_processor_logic(self):
        """Test Step 3: Core extraction logic for various file formats."""
        with patch('extraction_processor.s3_client') as mock_s3_client, \
             patch('extraction_processor.dynamodb') as mock_dynamo_res:
            
            mock_table = MagicMock()
            mock_dynamo_res.Table.return_value = mock_table
            
            # Sub-test: TXT extraction
            mock_response = {'Body': MagicMock()}
            mock_response['Body'].read.return_value = b"Hello TXT content"
            mock_s3_client.get_object.return_value = mock_response

            processor_event = {
                'Records': [{
                    's3': {
                        'bucket': {'name': self.bucket},
                        'object': {'key': 'test.txt'}
                    }
                }]
            }
            
            extraction_processor_mod.handler(processor_event, None)
            
            # Verify status update to COMPLETED with content
            calls = mock_table.update_item.call_args_list
            self.assertEqual(calls[1].kwargs['ExpressionAttributeValues'][':s'], 'COMPLETED')
            self.assertEqual(calls[1].kwargs['ExpressionAttributeValues'][':c'], 'Hello TXT content')

    def test_04_get_status_flow(self):
        """Test Step 4: Polling for the final extraction result."""
        with patch('get_status.dynamodb') as mock_dynamo_res:
            mock_table = MagicMock()
            mock_dynamo_res.Table.return_value = mock_table
            
            mock_table.get_item.return_value = {
                'Item': {
                    'fileId': self.file_id,
                    'status': 'COMPLETED',
                    'content': 'Hello TXT content'
                }
            }

            status_event = {
                'pathParameters': {'fileId': self.file_id}
            }
            
            response = get_status_mod.handler(status_event, None)
            self.assertEqual(response['statusCode'], 200)
            status_body = json.loads(response['body'])
            self.assertEqual(status_body['status'], 'COMPLETED')
            self.assertEqual(status_body['content'], 'Hello TXT content')

if __name__ == '__main__':
    unittest.main()
