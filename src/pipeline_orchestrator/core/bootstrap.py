"""Bootstrap module for pipeline initialization

Responsible for:
1. Loading and validating pipeline configuration
2. Setting up the core pipeline context
3. Initializing the extension system
"""
import logging
import os
from pathlib import Path
from typing import Optional
import yaml

from pipeline_orchestrator.models.pipeline import (
    PipelineConfig,
    PipelineDefinition,
    PipelineRawConfig
)
from pipeline_orchestrator.core.loader import ExtensionLoader
from pipeline_orchestrator.core.orchestrator import PipelineOrchestrator
from pipeline_orchestrator.interfaces.pulumi import PulumiInterface

class PipelineBootstrap:
    """Handles pipeline initialization and configuration loading"""
    
    def __init__(self):
        # Detect if running directly with Python (not through Pulumi)
        mock_mode = self.is_mock_mode()
        self.pulumi = PulumiInterface(mock_mode=mock_mode)
        self.logger = logging.getLogger("pipeline.bootstrap")
        self.config: Optional[PipelineConfig] = None
        self.pipeline: Optional[PipelineDefinition] = None
        
    def is_mock_mode(self) -> bool:
        """
        Determines if the code is running directly through Python (mock mode)
        or through Pulumi's runtime.
        """
        try:
            import pulumi
            # When running through pulumi runtime, we should be able to get a valid stack
            stack = pulumi.get_stack()
            if not stack:
                return True
            
            # Check if PULUMI_RUNTIME_VERSION env var is set
            # This is automatically set when running through `pulumi up`
            if not os.getenv('PULUMI_RUNTIME_VERSION'):
                return True
                
            return False
        except (ImportError, Exception):
            return True
            
        
    def load_configuration(self) -> None:
        """Load and validate pipeline configuration"""
        # Get configuration through Pulumi interface
        core_config = self.pulumi.get_pipeline_config()
        pipeline_file = Path(core_config['pipeline_config'])
        
        if not pipeline_file.exists():
            raise FileNotFoundError(f"Pipeline configuration file not found: {pipeline_file}")
            
        self.logger.info(f"Loading pipeline configuration from: {pipeline_file}")
        
        # Load raw YAML into initial model
        with open(pipeline_file) as f:
            raw_config = PipelineRawConfig(root=yaml.safe_load(f))
        
        # Get pipeline name and raw data
        pipeline_name = next(iter(raw_config.root.keys()))
        pipeline_data = raw_config.root[pipeline_name]
        
        # Extract core config and extensions
        core_config = pipeline_data.get('core', {})
        raw_extensions = raw_config.get_extensions()
        
        # Transform list extensions into dictionaries keyed by name
        extensions = {}
        for ext_type, items in raw_extensions.items():
            if not isinstance(items, list):
                raise ValueError(f"Extension {ext_type} must be a list of items")
            
            # Convert list of items into dictionary by name field
            extensions[ext_type] = {
                item['name']: item
                for item in items
                if 'name' in item
            }
            
            # Add mocked mode to extension
            # extensions[ext_type]["mocked_mode"] = self.pulumi.mock_mode
            
        # Transform into proper pipeline structure
        transformed = {
            pipeline_name: {
                'core': core_config,
                'extensions': extensions
            }
        }
        
        # Create and validate final config
        self.config = PipelineConfig(root=transformed)
        self.pipeline = self.config.get_pipeline()
        self.logger.info(f"Pipeline configuration loaded and validated with {len(extensions)} extensions")
        
    def create_orchestrator(self) -> PipelineOrchestrator:
        """Create and initialize the pipeline orchestrator"""
        if not self.pipeline:
            raise ValueError("Pipeline configuration not loaded")
            
        self.logger.info("Creating pipeline orchestrator")
        
        # Create orchestrator
        orchestrator = PipelineOrchestrator(
            parent_stack_name=self.pulumi.stack_name,
            pulumi=self.pulumi,
            pipeline=self.pipeline
        )
        
        # Initialize extension loader
        loader = ExtensionLoader(self.config)
        loader.discover_installed_extensions()
        extensions = loader.load_extensions()
        
        # Register extensions with orchestrator
        orchestrator.register_extensions(extensions)
        
        self.logger.info("Pipeline orchestrator created and initialized")
        return orchestrator