"""
Environmental Metrics API Service

A lightweight FastAPI service for collecting and storing environmental sensor data.
This service acts as the main entry point for metrics from multiple external sensors.

Requirements:
- Accept JSON payload with sensor_id, timestamp, and reading
- Store data in SQLite database
- Handle errors gracefully
- Provide health check endpoint

Architecture designed for scalability from 10 to 10,000+ sensors sending data every second.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List
import logging
import sys
from contextlib import asynccontextmanager

# Import local modules
from db.connection import get_db, init_db
from services.sensor_service import SensorService
from core.errors import SensorValidationError, DatabaseError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SensorReading(BaseModel):
    """Pydantic model for sensor reading validation."""
    sensor_id: str = Field(..., description="Unique identifier for the sensor")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    reading: float = Field(..., description="Environmental reading value")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = "healthy"
    timestamp: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup: Initialize database
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown: Cleanup can be added here if needed
    logger.info("Application shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Environmental Metrics API",
    description="API service for collecting environmental sensor data",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/readings", 
          response_model=dict,
          status_code=status.HTTP_201_CREATED,
          summary="Submit sensor reading",
          description="Accepts a JSON payload containing sensor_id, timestamp, and reading value")
async def submit_reading(
    reading_data: SensorReading,
    sensor_service: SensorService = Depends()
):
    """
    Submit a new sensor reading to the database.
    
    Args:
        reading_data: Validated sensor reading data
        sensor_service: Dependency-injected sensor service
        
    Returns:
        dict: Success message with reading ID
        
    Raises:
        HTTPException: 400 for validation errors, 500 for database errors
    """
    try:
        # Validate timestamp format
        try:
            datetime.fromisoformat(reading_data.timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise SensorValidationError("Invalid timestamp format. Expected ISO 8601 format.")
        
        # Submit reading
        reading_id = await sensor_service.submit_reading(
            sensor_id=reading_data.sensor_id,
            timestamp=reading_data.timestamp,
            value=reading_data.reading
        )
        
        logger.info(f"Successfully stored reading {reading_id} from sensor {reading_data.sensor_id}")
        
        return {
            "message": "Reading submitted successfully",
            "reading_id": reading_id,
            "sensor_id": reading_data.sensor_id
        }
        
    except SensorValidationError as e:
        logger.warning(f"Validation error for sensor {reading_data.sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(f"Database error while storing reading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store reading in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error while processing reading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.get("/api/v1/health", 
         response_model=HealthResponse,
         summary="Health check endpoint",
         description="Returns service health status")
async def health_check():
    """
    Health check endpoint to verify service availability.
    
    Returns:
        HealthResponse: Service status and current timestamp
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/api/v1/readings/{sensor_id}",
         response_model=List[dict],
         summary="Get readings for a specific sensor",
         description="Retrieve all readings for a specific sensor")
async def get_sensor_readings(
    sensor_id: str,
    sensor_service: SensorService = Depends()
):
    """
    Retrieve all readings for a specific sensor.
    
    Args:
        sensor_id: The ID of the sensor to retrieve readings for
        sensor_service: Dependency-injected sensor service
        
    Returns:
        List[dict]: List of readings for the specified sensor
        
    Raises:
        HTTPException: 404 if sensor not found, 500 for database errors
    """
    try:
        readings = await sensor_service.get_readings_by_sensor(sensor_id)
        
        if not readings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No readings found for sensor {sensor_id}"
            )
        
        return readings
        
    except DatabaseError as e:
        logger.error(f"Database error while retrieving readings for sensor {sensor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve readings from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error while retrieving readings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )