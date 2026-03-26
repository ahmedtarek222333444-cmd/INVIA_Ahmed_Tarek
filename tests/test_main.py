"""
Tests for the main FastAPI application.

This module contains integration tests for the API endpoints,
testing the complete request-response cycle.
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime

# Import the main app
from main import app, SensorReading, HealthResponse
from services.sensor_service import SensorService
from core.errors import SensorValidationError, DatabaseError


class TestMainAPI:
    """Test cases for the main API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI application."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_reading_data(self):
        """Sample sensor reading data for testing."""
        return {
            "sensor_id": "test-sensor-001",
            "timestamp": "2023-12-07T10:30:00Z",
            "reading": 23.5
        }
    
    @pytest.fixture
    def invalid_reading_data(self):
        """Invalid sensor reading data for testing validation."""
        return {
            "sensor_id": "test-sensor-001",
            "timestamp": "invalid-timestamp",
            "reading": 23.5
        }
    
    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        
        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        assert timestamp is not None
    
    @patch('main.SensorService')
    def test_submit_reading_success(self, mock_sensor_service, client, sample_reading_data):
        """Test successful submission of a sensor reading."""
        # Mock the sensor service
        mock_service_instance = AsyncMock()
        mock_service_instance.submit_reading.return_value = 123
        mock_sensor_service.return_value = mock_service_instance
        
        response = client.post(
            "/api/v1/readings",
            json=sample_reading_data
        )
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["message"] == "Reading submitted successfully"
        assert data["reading_id"] == 123
        assert data["sensor_id"] == sample_reading_data["sensor_id"]
        
        # Verify the service was called with correct parameters
        mock_service_instance.submit_reading.assert_called_once_with(
            sensor_id=sample_reading_data["sensor_id"],
            timestamp=sample_reading_data["timestamp"],
            value=sample_reading_data["reading"]
        )
    
    @patch('main.SensorService')
    def test_submit_reading_validation_error(self, mock_sensor_service, client, invalid_reading_data):
        """Test submission with invalid timestamp format."""
        # Mock the sensor service to raise validation error
        mock_service_instance = AsyncMock()
        mock_service_instance.submit_reading.side_effect = SensorValidationError("Invalid timestamp format")
        mock_sensor_service.return_value = mock_service_instance
        
        response = client.post(
            "/api/v1/readings",
            json=invalid_reading_data
        )
        
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "Invalid timestamp format" in data["detail"]
    
    @patch('main.SensorService')
    def test_submit_reading_database_error(self, mock_sensor_service, client, sample_reading_data):
        """Test submission with database error."""
        # Mock the sensor service to raise database error
        mock_service_instance = AsyncMock()
        mock_service_instance.submit_reading.side_effect = DatabaseError("Database connection failed")
        mock_sensor_service.return_value = mock_service_instance
        
        response = client.post(
            "/api/v1/readings",
            json=sample_reading_data
        )
        
        assert response.status_code == 500
        
        data = response.json()
        assert "detail" in data
        assert "Failed to store reading in database" in data["detail"]
    
    def test_submit_reading_invalid_json(self, client):
        """Test submission with invalid JSON payload."""
        response = client.post(
            "/api/v1/readings",
            json={"invalid": "payload"}
        )
        
        assert response.status_code == 422  # Validation error from Pydantic
    
    @patch('main.SensorService')
    def test_get_sensor_readings_success(self, mock_sensor_service, client):
        """Test successful retrieval of sensor readings."""
        # Mock the sensor service
        mock_service_instance = AsyncMock()
        mock_readings = [
            {
                "sensor_id": "test-sensor-001",
                "timestamp": "2023-12-07T10:30:00Z",
                "value": 23.5
            },
            {
                "sensor_id": "test-sensor-001",
                "timestamp": "2023-12-07T11:30:00Z",
                "value": 24.1
            }
        ]
        mock_service_instance.get_readings_by_sensor.return_value = mock_readings
        mock_sensor_service.return_value = mock_service_instance
        
        response = client.get("/api/v1/readings/test-sensor-001")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert data[0]["sensor_id"] == "test-sensor-001"
        assert data[0]["value"] == 23.5
        assert data[1]["value"] == 24.1
    
    @patch('main.SensorService')
    def test_get_sensor_readings_not_found(self, mock_sensor_service, client):
        """Test retrieval of readings for non-existent sensor."""
        # Mock the sensor service to return empty list
        mock_service_instance = AsyncMock()
        mock_service_instance.get_readings_by_sensor.return_value = []
        mock_sensor_service.return_value = mock_service_instance
        
        response = client.get("/api/v1/readings/non-existent-sensor")
        
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "No readings found for sensor non-existent-sensor" in data["detail"]
    
    @patch('main.SensorService')
    def test_get_sensor_readings_database_error(self, mock_sensor_service, client):
        """Test retrieval with database error."""
        # Mock the sensor service to raise database error
        mock_service_instance = AsyncMock()
        mock_service_instance.get_readings_by_sensor.side_effect = DatabaseError("Database query failed")
        mock_sensor_service.return_value = mock_service_instance
        
        response = client.get("/api/v1/readings/test-sensor-001")
        
        assert response.status_code == 500
        
        data = response.json()
        assert "detail" in data
        assert "Failed to retrieve readings from database" in data["detail"]


class TestPydanticModels:
    """Test cases for Pydantic models."""
    
    def test_sensor_reading_valid(self):
        """Test valid sensor reading model creation."""
        data = {
            "sensor_id": "sensor-001",
            "timestamp": "2023-12-07T10:30:00Z",
            "reading": 23.5
        }
        
        reading = SensorReading(**data)
        assert reading.sensor_id == "sensor-001"
        assert reading.timestamp == "2023-12-07T10:30:00Z"
        assert reading.reading == 23.5
    
    def test_sensor_reading_missing_field(self):
        """Test sensor reading model with missing required field."""
        data = {
            "sensor_id": "sensor-001",
            "timestamp": "2023-12-07T10:30:00Z"
            # Missing 'reading' field
        }
        
        with pytest.raises(ValueError):
            SensorReading(**data)
    
    def test_sensor_reading_invalid_type(self):
        """Test sensor reading model with invalid field type."""
        data = {
            "sensor_id": "sensor-001",
            "timestamp": "2023-12-07T10:30:00Z",
            "reading": "not-a-number"  # Should be float
        }
        
        with pytest.raises(ValueError):
            SensorReading(**data)
    
    def test_health_response_valid(self):
        """Test valid health response model creation."""
        data = {
            "status": "healthy",
            "timestamp": "2023-12-07T10:30:00Z"
        }
        
        response = HealthResponse(**data)
        assert response.status == "healthy"
        assert response.timestamp == "2023-12-07T10:30:00Z"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])