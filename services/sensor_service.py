"""
Sensor service module for handling sensor reading operations.

This module provides business logic for sensor data operations including
submitting readings, retrieving sensor data, and managing sensor records.
It follows the .clinerules guidelines for clean, maintainable code.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from db.connection import get_db, DatabaseError

logger = logging.getLogger(__name__)


class SensorService:
    """
    Service class for handling sensor-related operations.
    
    This service encapsulates all business logic related to sensor data
    management, providing a clean interface between the API layer and
    database operations.
    """
    
    def __init__(self):
        """Initialize the sensor service."""
        pass
    
    async def submit_reading(
        self, 
        sensor_id: str, 
        timestamp: str, 
        value: float
    ) -> int:
        """
        Submit a new sensor reading to the database.
        
        This method handles the complete workflow for storing a sensor reading:
        1. Ensure the sensor exists (create if necessary)
        2. Insert the reading record
        3. Return the created reading ID
        
        Args:
            sensor_id: Unique identifier for the sensor
            timestamp: ISO 8601 formatted timestamp string
            value: The sensor reading value
            
        Returns:
            int: The ID of the created reading record
            
        Raises:
            DatabaseError: If database operations fail
        """
        try:
            # Use dependency injection to get database connection
            db = await get_db()
            try:
                # First, ensure the sensor exists
                await self._ensure_sensor_exists(db, sensor_id)
                
                # Insert the reading
                query = """
                INSERT INTO readings (sensor_id, timestamp, value)
                VALUES (?, ?, ?)
                """
                
                await db.execute(query, (sensor_id, timestamp, value))
                await db.commit()
                
                # Get the ID of the inserted record
                # For aiosqlite, we need to get the last row ID differently
                cursor = await db.execute("SELECT last_insert_rowid()")
                result = await cursor.fetchone()
                reading_id = result[0] if result else None
                
                logger.debug(f"Inserted reading {reading_id} for sensor {sensor_id}")
                return reading_id
            finally:
                await db.close()
                
        except Exception as e:
            logger.error(f"Failed to submit reading for sensor {sensor_id}: {e}")
            raise DatabaseError(f"Failed to submit reading: {e}")
    
    async def get_readings_by_sensor(
        self, 
        sensor_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve all readings for a specific sensor.
        
        Args:
            sensor_id: The ID of the sensor to retrieve readings for
            limit: Optional limit on the number of readings to return
            
        Returns:
            List[Dict]: List of reading records with sensor_id, timestamp, and value
            
        Raises:
            DatabaseError: If database operations fail
        """
        try:
            async with get_db() as db:
                # Query readings for the specified sensor
                query = """
                SELECT sensor_id, timestamp, value
                FROM readings
                WHERE sensor_id = ?
                ORDER BY timestamp DESC
                """
                
                params = [sensor_id]
                
                # Add limit if specified
                if limit is not None:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                # Convert to list of dictionaries
                readings = [
                    {
                        "sensor_id": row[0],
                        "timestamp": row[1],
                        "value": row[2]
                    }
                    for row in rows
                ]
                
                logger.debug(f"Retrieved {len(readings)} readings for sensor {sensor_id}")
                return readings
                
        except Exception as e:
            logger.error(f"Failed to retrieve readings for sensor {sensor_id}: {e}")
            raise DatabaseError(f"Failed to retrieve readings: {e}")
    
    async def get_sensor_stats(
        self, 
        sensor_id: str
    ) -> Dict:
        """
        Get statistics for a specific sensor.
        
        Args:
            sensor_id: The ID of the sensor to get statistics for
            
        Returns:
            Dict: Statistics including count, min, max, and average values
            
        Raises:
            DatabaseError: If database operations fail
        """
        try:
            async with get_db() as db:
                query = """
                SELECT 
                    COUNT(*) as count,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    AVG(value) as avg_value
                FROM readings
                WHERE sensor_id = ?
                """
                
                cursor = await db.execute(query, (sensor_id,))
                row = await cursor.fetchone()
                
                if row and row[0] > 0:  # If there are readings
                    stats = {
                        "sensor_id": sensor_id,
                        "count": row[0],
                        "min_value": round(row[1], 2),
                        "max_value": round(row[2], 2),
                        "avg_value": round(row[3], 2)
                    }
                else:
                    stats = {
                        "sensor_id": sensor_id,
                        "count": 0,
                        "min_value": None,
                        "max_value": None,
                        "avg_value": None
                    }
                
                logger.debug(f"Calculated stats for sensor {sensor_id}: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"Failed to calculate stats for sensor {sensor_id}: {e}")
            raise DatabaseError(f"Failed to calculate statistics: {e}")
    
    async def _ensure_sensor_exists(self, db: any, sensor_id: str) -> None:
        """
        Ensure a sensor record exists in the database.
        
        This is a private helper method that creates a sensor record if it doesn't
        already exist. It's used internally by submit_reading to maintain referential
        integrity.
        
        Args:
            db: Database connection
            sensor_id: The sensor ID to ensure exists
            
        Raises:
            DatabaseError: If database operations fail
        """
        try:
            # Check if sensor already exists
            query = "SELECT 1 FROM sensors WHERE sensor_id = ? LIMIT 1"
            cursor = await db.execute(query, (sensor_id,))
            exists = await cursor.fetchone()
            
            if not exists:
                # Insert new sensor record
                insert_query = """
                INSERT INTO sensors (sensor_id)
                VALUES (?)
                """
                await db.execute(insert_query, (sensor_id,))
                await db.commit()
                
                logger.debug(f"Created new sensor record for {sensor_id}")
                
        except Exception as e:
            logger.error(f"Failed to ensure sensor exists: {sensor_id}: {e}")
            raise DatabaseError(f"Failed to ensure sensor exists: {e}")