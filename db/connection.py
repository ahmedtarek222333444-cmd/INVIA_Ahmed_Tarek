"""
Database connection module using aiosqlite for async SQLite operations.

This module provides database connection management and initialization functions
following the .clinerules guidelines for direct SQLite access with proper error handling.
"""

import aiosqlite
import logging
from typing import AsyncGenerator
import os

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = os.getenv("DATABASE_URL", "sensor_data.db")


async def init_db():
    """
    Initialize the database by creating necessary tables.
    
    This function creates the sensors and readings tables if they don't exist.
    It's designed to be called once during application startup.
    
    Raises:
        DatabaseError: If database initialization fails
    """
    try:
        # Create tables using explicit SQL statements
        create_sensors_table = """
        CREATE TABLE IF NOT EXISTS sensors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_readings_table = """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            value REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sensor_id) REFERENCES sensors (sensor_id)
        )
        """
        
        # Create indexes for better query performance
        create_sensor_index = """
        CREATE INDEX IF NOT EXISTS idx_readings_sensor_id ON readings (sensor_id)
        """
        
        create_timestamp_index = """
        CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings (timestamp)
        """
        
        # Execute all statements in a single connection
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(create_sensors_table)
            await db.execute(create_readings_table)
            await db.execute(create_sensor_index)
            await db.execute(create_timestamp_index)
            await db.commit()
            
        logger.info(f"Database initialized successfully at {DB_PATH}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}")


async def get_db() -> aiosqlite.Connection:
    """
    Get a database connection for use in dependency injection.
    
    This function provides a database connection that can be used with FastAPI's
    dependency injection system. The connection is automatically closed when the
    context manager exits.
    
    Returns:
        aiosqlite.Connection: Database connection
        
    Raises:
        DatabaseError: If database connection fails
    """
    try:
        db = await aiosqlite.connect(DB_PATH)
        # Enable foreign key constraints
        await db.execute("PRAGMA foreign_keys = ON")
        return db
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise DatabaseError(f"Failed to connect to database: {e}")


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass