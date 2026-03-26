"""
Custom error classes for the Environmental Metrics API.

This module defines custom exception classes that provide clear, specific error
messages for different failure scenarios in the application. Following the
.clinerules guidelines, these errors help with proper error handling and logging.
"""

from typing import Optional


class SensorValidationError(Exception):
    """
    Exception raised for sensor data validation errors.
    
    This exception is raised when sensor data fails validation, such as
    invalid timestamp formats or missing required fields.
    """
    
    def __init__(self, message: str, field: Optional[str] = None):
        """
        Initialize the validation error.
        
        Args:
            message: Human-readable error message
            field: Optional field name that caused the validation error
        """
        self.message = message
        self.field = field
        super().__init__(self.message)
    
    def __str__(self):
        """String representation of the error."""
        if self.field:
            return f"SensorValidationError in field '{self.field}': {self.message}"
        return f"SensorValidationError: {self.message}"


class DatabaseError(Exception):
    """
    Exception raised for database-related errors.
    
    This exception wraps database operation failures and provides
    consistent error handling across the application.
    """
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize the database error.
        
        Args:
            message: Human-readable error message
            original_error: Optional original exception that caused this error
        """
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
    
    def __str__(self):
        """String representation of the error."""
        if self.original_error:
            return f"DatabaseError: {self.message} (Original: {self.original_error})"
        return f"DatabaseError: {self.message}"


class SensorNotFoundError(Exception):
    """
    Exception raised when a sensor is not found in the database.
    
    This exception is raised when attempting to retrieve data for a
    sensor that doesn't exist in the system.
    """
    
    def __init__(self, sensor_id: str):
        """
        Initialize the sensor not found error.
        
        Args:
            sensor_id: The ID of the sensor that was not found
        """
        self.sensor_id = sensor_id
        self.message = f"Sensor with ID '{sensor_id}' not found"
        super().__init__(self.message)
    
    def __str__(self):
        """String representation of the error."""
        return f"SensorNotFoundError: {self.message}"


class RateLimitExceededError(Exception):
    """
    Exception raised when rate limits are exceeded.
    
    This exception is raised when a client exceeds the allowed number
    of requests within a specified time period.
    """
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        """
        Initialize the rate limit error.
        
        Args:
            message: Human-readable error message
            retry_after: Optional number of seconds to wait before retrying
        """
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)
    
    def __str__(self):
        """String representation of the error."""
        if self.retry_after:
            return f"RateLimitExceededError: {self.message} (Retry after: {self.retry_after}s)"
        return f"RateLimitExceededError: {self.message}"


class ConfigurationError(Exception):
    """
    Exception raised for configuration-related errors.
    
    This exception is raised when the application configuration is
    invalid or missing required settings.
    """
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        """
        Initialize the configuration error.
        
        Args:
            message: Human-readable error message
            config_key: Optional configuration key that caused the error
        """
        self.message = message
        self.config_key = config_key
        super().__init__(self.message)
    
    def __str__(self):
        """String representation of the error."""
        if self.config_key:
            return f"ConfigurationError for '{self.config_key}': {self.message}"
        return f"ConfigurationError: {self.message}"