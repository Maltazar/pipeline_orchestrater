"""Extension Loader

Responsible for:
1. Discovering installed extensions in the extensions directory and pip environment
2. Loading required extensions specified in pipeline configuration
3. Validating extension compatibility
4. Managing extension registration
"""

import logging
import sys
from importlib import import_module
from typing import Dict, Type, Any
from pathlib import Path

from pipeline_orchestrator.models.pipeline import PipelineConfig
from pipeline_orchestrator.handlers.extension import ExtensionHandler
from pipeline_orchestrator.core.errors import (
    ExtensionNotFoundError,
    ExtensionLoadError,
    ExtensionValidationError
)

class ExtensionLoader:
    """Dynamic extension loader"""
    
    EXTENSION_PACKAGE_PREFIX = "pipeline_orchestrator_extension_"
    EXTENSION_CLASS_SUFFIX = "Extension"
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger("pipeline.loader")
        self.installed_extensions: Dict[str, str] = {}  # Maps extension name to module path
        self.loaded_extensions: Dict[str, Type[ExtensionHandler]] = {}
        self.extension_dir = None
        
    def get_extension_status(self) -> Dict[str, Any]:
        """Get current status of extension discovery and loading
        
        Returns a dictionary containing:
            required: Extensions required by pipeline configuration
            installed: Extensions found in extensions directory
            loaded: Extensions successfully loaded
            missing: Required extensions that are not installed
            extra: Installed extensions not required by configuration
        """
        pipeline = self.config.get_pipeline()
        required = set(pipeline.extensions.keys())
        installed = set(self.installed_extensions.keys())
        loaded = set(self.loaded_extensions.keys())
        
        return {
            "required": list(required),
            "installed": list(installed),
            "loaded": list(loaded),
            "missing": list(required - installed),
            "extra": list(installed - required)
        }
        
    def discover_pip_installed_extensions(self) -> Dict[str, str]:
        """Find pip-installed extensions in the Python environment
        
        Looks for installed packages that follow the naming convention:
        pulumi-orchestrator-extension-{name}
        
        Returns:
            Dict mapping extension names to their module paths
        """
        self.logger.info("Starting pip-installed extension discovery")
        
        for path in sys.path:
            if not path:
                continue
                
            path_obj = Path(path)
            if not path_obj.exists():
                continue
                
            # Look for packages matching our naming convention
            for item in path_obj.glob(f"{self.EXTENSION_PACKAGE_PREFIX}*"):
                if not item.is_dir():
                    continue
                    
                # Extract extension name from package name
                extension_name = item.name.replace(self.EXTENSION_PACKAGE_PREFIX, "")
                
                # Use the package name directly as the module path
                module_path = item.name
                self.installed_extensions[extension_name] = module_path
                self.logger.info(f"Found pip-installed extension: {extension_name} -> {module_path}")
        
        return self.installed_extensions

    def discover_directory_extensions(self) -> Dict[str, str]:
        """Find installed extensions in the extensions directory
        
        Scans the extensions directory for valid extension packages.
        An extension is considered installed if it follows the naming convention:
        pipeline_orchestrator_extension_{name}
        
        Returns:
            Dict mapping extension names to their module paths
        """
        self.logger.info("Starting directory extension discovery")
        
        if not self.extension_dir or not self.extension_dir.exists():
            self.logger.info("No extension directory specified or directory does not exist")
            return {}
            
        for item in self.extension_dir.iterdir():
            if item.is_dir() and item.name.startswith(self.EXTENSION_PACKAGE_PREFIX):
                extension_name = item.name.replace(self.EXTENSION_PACKAGE_PREFIX, "")
                
                # Add extension directory to Python path if not already there
                if str(self.extension_dir) not in sys.path:
                    sys.path.insert(0, str(self.extension_dir))
                    self.logger.debug(f"Added {self.extension_dir} to sys.path")
                
                # Use the package name as the module path
                module_path = item.name
                self.installed_extensions[extension_name] = module_path
                self.logger.info(f"Found directory extension: {extension_name} -> {module_path}")
        
        return self.installed_extensions
        
    def discover_installed_extensions(self) -> Dict[str, str]:
        """Find all installed extensions from both pip packages and directory
        
        Returns:
            Dict mapping extension names to their module paths
        """
        self.logger.info("Starting extension discovery")
        
        # Get required extensions from config
        pipeline = self.config.get_pipeline()
        extension_dir = pipeline.core.extension_dir
        if extension_dir:
            self.extension_dir = Path(extension_dir)
        required_extensions = set(pipeline.extensions.keys())
        self.logger.info(f"Extensions required by pipeline: {required_extensions}")
        
        # Clear existing discoveries
        self.installed_extensions.clear()
        
        # Discover extensions from both sources
        self.discover_pip_installed_extensions()
        self.discover_directory_extensions()
        
        installed = set(self.installed_extensions.keys())
        self.logger.info(f"Total installed extensions found: {installed}")
        
        # Report on extension status
        missing_extensions = required_extensions - installed
        if missing_extensions:
            self.logger.warning(f"Required extensions not installed: {missing_extensions}")
        
        extra_extensions = installed - required_extensions
        if extra_extensions:
            self.logger.info(f"Extra extensions installed but not required: {extra_extensions}")
            
        status = self.get_extension_status()
        self.logger.info(f"Discovery complete. Found {len(self.installed_extensions)} installed extensions")
        self.logger.debug(f"Extension discovery status: {status}")
        
        return self.installed_extensions
            
    def validate_extension(self, name: str, extension_class: Type[Any]) -> bool:
        """Validate an extension class meets requirements"""
        # Must inherit from ExtensionHandler
        if not issubclass(extension_class, ExtensionHandler):
            raise ExtensionValidationError(
                f"Invalid extension class for {name}",
                name,
                {"error": "Class must inherit from ExtensionHandler"}
            )
            
        # Must implement required methods
        required_methods = ['validate_config', 'execute', 'cleanup']
        missing_methods = [
            method for method in required_methods
            if not callable(getattr(extension_class, method, None))
        ]
        
        if missing_methods:
            raise ExtensionValidationError(
                f"Extension {name} missing required methods",
                name,
                {"missing_methods": missing_methods}
            )
            
        return True
            
    def load_extension(self, name: str) -> Type[ExtensionHandler]:
        """Dynamically load an extension handler class
        
        Args:
            name: Name of the extension to load
            
        Returns:
            Extension handler class
            
        Raises:
            ExtensionNotFoundError: If extension module cannot be found
            ExtensionLoadError: If extension cannot be loaded
            ExtensionValidationError: If extension fails validation
        """
        try:
            if name not in self.installed_extensions:
                raise ExtensionNotFoundError(name)
                
            module_path = self.installed_extensions[name]
            class_name = f"{name.title()}{self.EXTENSION_CLASS_SUFFIX}"
            
            self.logger.info(f"Loading extension module: {module_path}")
            
            # Import the module
            try:
                self.logger.debug(f"Importing module: {module_path}")
                module = import_module(module_path)
                
                # Get the extension class
                if not hasattr(module, class_name):
                    available = [name for name in dir(module) if name.endswith(self.EXTENSION_CLASS_SUFFIX)]
                    self.logger.debug(f"Available extension classes: {available}")
                    raise ExtensionLoadError(
                        f"Could not find {class_name} in {module_path}",
                        name,
                        {"available_classes": available}
                    )
                
                extension_class = getattr(module, class_name)
                
                # Validate the extension
                self.logger.info(f"Validating extension: {name}")
                self.validate_extension(name, extension_class)
                
                # Store the loaded extension
                self.loaded_extensions[name] = extension_class
                self.logger.info(f"Successfully loaded extension: {name}")
                
                return extension_class
                
            except ImportError as e:
                self.logger.error(f"Import error: {str(e)}")
                raise ExtensionLoadError(
                    f"Failed to import {module_path}",
                    name,
                    {"error": str(e)}
                )
                
        except Exception as e:
            self.logger.error(f"Failed to load extension {name}: {str(e)}")
            raise

    def load_extensions(self) -> Dict[str, Type[ExtensionHandler]]:
        """Load all required extensions that are installed
        
        Only loads extensions that are both:
        1. Required by the pipeline configuration
        2. Found during discovery
        
        Returns:
            Dict mapping extension names to their handler classes
        """
        self.logger.info("Loading required extensions")
        
        # Get required extensions that are installed
        pipeline = self.config.get_pipeline()
        required_extensions = set(pipeline.extensions.keys())
        available_extensions = required_extensions & set(self.installed_extensions.keys())
        
        # Load each extension
        for name in available_extensions:
            try:
                self.load_extension(name)
            except (ExtensionNotFoundError, ExtensionLoadError, ExtensionValidationError) as e:
                self.logger.error(f"Failed to load extension {name}: {str(e)}")
                
        status = self.get_extension_status()
        self.logger.info(f"Extension loading complete. Status: {status}")
        
        return self.loaded_extensions 