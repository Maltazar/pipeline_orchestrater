"""Core Pipeline Orchestrator

Responsible for:
1. Managing pipeline execution flow
2. Coordinating between extensions
3. Managing global pipeline state
4. Controlling information flow
"""

import logging
from typing import Dict, Any, Type
from pipeline_orchestrator.models.pipeline import PipelineDefinition
from pipeline_orchestrator.interfaces.pulumi import PulumiInterface
from pipeline_orchestrator.handlers.extension import ExtensionHandler
from pipeline_orchestrator.core.context import ExtensionContext
from pipeline_orchestrator.core.state import PipelineState
from pipeline_orchestrator.core.errors import (
    ErrorHandler,
    ExtensionValidationError,
    StateError
)

class PipelineOrchestrator:
    """Core pipeline orchestrator that manages execution flow"""
    
    def __init__(self, parent_stack_name: str, pulumi: PulumiInterface, pipeline: PipelineDefinition):
        self.parent_stack_name = parent_stack_name
        self.pulumi = pulumi
        self.pipeline = pipeline
        self.extensions: Dict[str, ExtensionHandler] = {}
        self.state = PipelineState()
        self.logger = logging.getLogger("pipeline.orchestrator")
        self.error_handler = ErrorHandler(self.logger)
        
    def register_extensions(self, loaded_extensions: Dict[str, Type[ExtensionHandler]]) -> None:
        """Register pre-loaded extensions with the orchestrator"""
        for name, extension_cls in loaded_extensions.items():
            try:
                extension = extension_cls()
                extension.initialize(name, self.parent_stack_name, self.pulumi)
                self.extensions[name] = extension
                self.state.set_extension_state(name, 'registered')
                self.logger.info(f"Extension {name} registered successfully")
            except Exception as e:
                self.error_handler.handle_error(e, f"extension.{name}")
        
    def get_extension_config(self, extension_name: str) -> Dict[str, Any]:
        """Get configuration for a specific extension with resolved references"""
        raw_config = self.pipeline.extensions.get(extension_name, {})  # Default to empty dict if not found
        if not raw_config:
            self.logger.warning(f"No configuration found for extension: {extension_name}")
        return self.state.resolve_references(raw_config)
        
    def execute(self) -> None:
        """Execute the pipeline flow
        
        Coordinates extension execution and manages global state.
        Each extension handles its own validation and execution.
        """
        self.logger.info("Starting pipeline execution")
        
        # Load secrets first if secrets extension is present
        if 'secrets' in self.pipeline.extensions:
            self.logger.info("Loading secrets")
            self.state.load_secrets(self.pipeline.extensions['secrets'])
        
        # Execute each extension with context management
        for name, extension in self.extensions.items():
            if name not in self.pipeline.extensions:
                self.logger.warning(f"Skipping unconfigured extension: {name}")
                continue
                
            self.logger.info(f"Processing extension: {name}")
            self.state.set_extension_state(name, 'starting')
            config = self.get_extension_config(name)
            if not config:
                continue
                
            try:
                with ExtensionContext(extension):
                    self.logger.info(f"Validating configuration for {name}")
                    try:
                        extension.validate_config(config)
                    except Exception as e:
                        raise ExtensionValidationError(
                            f"Configuration validation failed for {name}",
                            name,
                            {"error": str(e)}
                        )
                        
                    self.logger.info(f"Executing extension: {name}")
                    extension.execute(config)
                    
                    # Store any data produced by the extension
                    if hasattr(extension, 'get_output_data'):
                        self.logger.info(f"Storing output data for {name}")
                        self.state.store_extension_data(name, extension.get_output_data())
                        
                    self.state.set_extension_state(name, 'success')
                    self.logger.info(f"Extension {name} completed successfully")
            except Exception as e:
                self.state.set_extension_state(name, 'failed')
                self.error_handler.handle_error(e, f"extension.{name}")
                
        self.logger.info("Pipeline execution completed")
            
    def cleanup(self) -> None:
        """Coordinate cleanup of all extensions
        
        Ensures proper cleanup of resources even if some extensions fail.
        Logs all cleanup operations and handles errors appropriately.
        """
        self.logger.info("Starting pipeline cleanup")
        cleanup_errors = []
        
        # Clean up extensions in reverse order
        for name, extension in reversed(list(self.extensions.items())):
            self.logger.info(f"Cleaning up extension: {name}")
            try:
                extension.cleanup()
                self.state.set_extension_state(name, 'cleaned')
                self.logger.info(f"Extension {name} cleaned up successfully")
            except Exception as e:
                cleanup_errors.append((name, e))
                self.state.set_extension_state(name, 'cleanup_failed')
                self.error_handler.handle_error(e, f"extension.{name}.cleanup")
                
        # Handle any cleanup errors
        if cleanup_errors:
            error_details = {
                "failed_extensions": [name for name, _ in cleanup_errors],
                "error_count": len(cleanup_errors)
            }
            raise StateError("Cleanup failed for some extensions", error_details)
