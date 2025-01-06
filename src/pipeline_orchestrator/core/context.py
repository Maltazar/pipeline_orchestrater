"""Context Management for Pipeline Extensions

Responsible for:
1. Managing extension lifecycle
2. Ensuring proper cleanup
3. Handling state transitions
4. Error boundary management
"""

import logging
from typing import TypeVar, Type
from pipeline_orchestrator.handlers.extension import ExtensionHandler

T = TypeVar('T', bound=ExtensionHandler)

class ExtensionContext:
    """Context manager for extension execution"""
    
    def __init__(self, extension: ExtensionHandler):
        self.extension = extension
        self.logger = logging.getLogger("pipeline.context")
        
    def __enter__(self):
        """Setup extension context"""
        return self.extension
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure cleanup on exit"""
        try:
            self.extension.cleanup()
        except Exception as e:
            self.logger.error(f"Error during extension cleanup: {str(e)}", exc_info=True)
        return False  # Don't suppress exceptions
        
def with_extension(extension_cls: Type[T]) -> T:
    """Decorator for extension execution with context management"""
    def wrapper(*args, **kwargs):
        with ExtensionContext(extension_cls()) as ext:
            return ext.execute(*args, **kwargs)
    return wrapper 