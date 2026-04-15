import os
import pytest
import io

# Set environment variables BEFORE importing app
os.environ["BUCKET_NAME"] = "test-bucket"
os.environ["TABLE_NAME"] = "test-table"
os.environ["SECRET_CODE"] = "test-secret"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.monolith.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_root_path():
    response = client.get("/")
    assert response.status_code == 200
    assert "Text Extractor Dashboard" in response.text

@patch("backend.monolith.main.s3_client")
@patch("backend.monolith.main.dynamodb")
def test_process_endpoint_success(mock_dynamo, mock_s3):
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table
    
    file_content = b"Hello, this is a test file."
    file_name = "test.txt"
    
    # Mock BackgroundTasks.add_task to avoid running the actual processing
    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post(
            "/api/process",
            files={"file": (file_name, file_content, "text/plain")},
            headers={"X-Secret-Code": "test-secret"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "fileId" in data
    assert data["message"] == "Extraction started"
    
    # Verify S3 upload
    mock_s3.put_object.assert_called_once()
    args, kwargs = mock_s3.put_object.call_args
    assert kwargs["Bucket"] == "test-bucket"
    assert kwargs["Key"].startswith("uploads/")
    assert kwargs["Key"].endswith(".txt")
    assert kwargs["Body"] == file_content
    assert kwargs["ContentType"] == "text/plain"
    
    # Verify DynamoDB initialization
    mock_table.put_item.assert_called_once()
    put_args, put_kwargs = mock_table.put_item.call_args
    item = put_kwargs["Item"]
    assert item["fileId"] == data["fileId"]
    assert item["status"] == "PENDING"
    
    # Verify Background Task
    mock_add_task.assert_called_once()

@patch("backend.monolith.main.s3_client")
@patch("backend.monolith.main.dynamodb")
@patch("backend.monolith.main.extract_text")
def test_full_process_flow(mock_extract, mock_dynamo, mock_s3):
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table
    
    # Mock S3 get_object for process_extraction
    mock_s3.get_object.return_value = {
        'Body': io.BytesIO(b"test content")
    }
    mock_extract.return_value = "Extracted Text"
    
    file_content = b"test content"
    file_name = "test.txt"
    
    # In this test, we DON'T mock BackgroundTasks.add_task
    # We want to see if it triggers process_extraction
    # But since BackgroundTasks runs after response is sent, 
    # and TestClient runs in-process, we might need to be careful.
    # Actually, TestClient with BackgroundTasks works fine, it runs them before returning if not using async.
    # Wait, FastAPI BackgroundTasks run AFTER the response is sent.
    
    response = client.post(
        "/api/process",
        files={"file": (file_name, file_content, "text/plain")},
        headers={"X-Secret-Code": "test-secret"}
    )
    
    assert response.status_code == 200
    file_id = response.json()["fileId"]
    
    # Verify S3 put_object (upload)
    mock_s3.put_object.assert_called_once()
    
    # Verify DynamoDB initial put_item
    # It should have been called once in the endpoint
    assert mock_table.put_item.call_count == 1
    
    # Since BackgroundTasks might run asynchronously even in TestClient 
    # (actually for TestClient it usually runs them), 
    # we might need to wait or just check if they were triggered.
    # If we want to be sure process_extraction was called, we can check mock_s3.get_object
    
    # To ensure BackgroundTasks run, we might need to use a context manager or just wait.
    # In FastAPI TestClient, background tasks ARE executed.
    
    # Verify process_extraction was called
    mock_s3.get_object.assert_called_once()
    mock_extract.assert_called_once()
    
    # Verify DynamoDB status updates (PROCESSING and COMPLETED)
    # 1 put_item + 2 update_item calls
    assert mock_table.update_item.call_count == 2

def test_process_endpoint_invalid_secret():
    file_content = b"Hello, this is a test file."
    file_name = "test.txt"
    
    response = client.post(
        "/api/process",
        files={"file": (file_name, file_content, "text/plain")},
        headers={"X-Secret-Code": "wrong-secret"}
    )
    assert response.status_code == 403

def test_process_endpoint_missing_file():
    response = client.post(
        "/api/process",
        headers={"X-Secret-Code": "test-secret"}
    )
    assert response.status_code == 422 # Unprocessable Entity (FastAPI validation error)
