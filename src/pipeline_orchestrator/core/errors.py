"""Error Handling System for Pipeline

Responsible for:
1. Custom pipeline exceptions
2. Error categorization
3. Error recovery strategies
4. Extension error handling
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class ErrorSeverity(Enum):
    """Severity levels for pipeline errors"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Categories of pipeline errors"""
    CONFIGURATION = "configuration"
    EXTENSION = "extension"
    RESOURCE = "resource"
    STATE = "state"
    SYSTEM = "system"

@dataclass
class PipelineError:
    """Structured error information"""
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: str
    details: Optional[Dict[str, Any]] = None
    original_error: Optional[Exception] = None

class PipelineConfigurationError(Exception):
    """Error in pipeline configuration"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_info = PipelineError(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.CONFIGURATION,
            context="configuration",
            details=details
        )

class ExtensionNotFoundError(Exception):
    """Extension module could not be found"""
    def __init__(self, extension_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"Extension not found: {extension_name}"
        super().__init__(message)
        self.error_info = PipelineError(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXTENSION,
            context=f"extension.{extension_name}",
            details=details
        )

class ExtensionLoadError(Exception):
    """Error loading extension module"""
    def __init__(self, message: str, extension_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_info = PipelineError(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXTENSION,
            context=f"extension.{extension_name}",
            details=details
        )

class ExtensionValidationError(Exception):
    """Extension failed validation"""
    def __init__(self, message: str, extension_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_info = PipelineError(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXTENSION,
            context=f"extension.{extension_name}",
            details=details
        )

class StateError(Exception):
    """Error in pipeline state management"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_info = PipelineError(
            message=message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.STATE,
            context="state",
            details=details
        )

class ErrorHandler:
    """Handles pipeline errors and recovery strategies"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def handle_error(self, error: Exception, context: str) -> None:
        """Handle an error based on its type and severity"""
        if hasattr(error, 'error_info'):
            error_info = error.error_info
        else:
            # Create generic error info for unknown errors
            error_info = PipelineError(
                message=str(error),
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.SYSTEM,
                context=context,
                original_error=error
            )
            
        # Log the error with details
        error_msg = f"Error in {error_info.context}: {error_info.message}"
        if error_info.details:
            error_msg += f" Details: {error_info.details}"
            
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error_msg, exc_info=True)
            raise error
        elif error_info.severity == ErrorSeverity.ERROR:
            self.logger.error(error_msg, exc_info=True)
            if error_info.category != ErrorCategory.EXTENSION:
                raise error
        elif error_info.severity == ErrorSeverity.WARNING:
            self.logger.warning(error_msg)
        else:
            self.logger.info(error_msg) 