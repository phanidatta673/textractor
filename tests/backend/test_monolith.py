import os
import pytest

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

@patch("backend.monolith.main.s3_client")
def test_get_presigned_url(mock_s3):
    mock_s3.generate_presigned_url.return_value = "https://mock-url"
    
    response = client.post(
        "/api/presigned-url",
        json={"filename": "test.txt", "contentType": "text/plain"},
        headers={"X-Secret-Code": "test-secret"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "uploadUrl" in data
    assert data["uploadUrl"] == "https://mock-url"
    assert "fileId" in data
    assert "key" in data

def test_get_presigned_url_invalid_secret():
    response = client.post(
        "/api/presigned-url",
        json={"filename": "test.txt", "contentType": "text/plain"},
        headers={"X-Secret-Code": "wrong-secret"}
    )
    assert response.status_code == 403

@patch("backend.monolith.main.dynamodb")
def test_start_extraction(mock_dynamo):
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table
    
    # We mock process_extraction to avoid background execution during unit test if possible
    # or just let it run if it's also mocked inside.
    with patch("backend.monolith.main.process_extraction") as mock_process:
        response = client.post(
            "/api/start",
            json={"fileId": "test-id", "key": "uploads/test.txt", "bucket": "test-bucket"},
            headers={"X-Secret-Code": "test-secret"}
        )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Extraction started"
    mock_table.put_item.assert_called_once()

@patch("backend.monolith.main.dynamodb")
def test_get_status(mock_dynamo):
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table
    mock_table.get_item.return_value = {"Item": {"fileId": "test-id", "status": "COMPLETED", "content": "Extracted text"}}
    
    response = client.get("/api/status/test-id")
    
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["content"] == "Extracted text"

@patch("backend.monolith.main.dynamodb")
def test_get_status_not_found(mock_dynamo):
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table
    mock_table.get_item.return_value = {}
    
    response = client.get("/api/status/not-found")
    assert response.status_code == 404
