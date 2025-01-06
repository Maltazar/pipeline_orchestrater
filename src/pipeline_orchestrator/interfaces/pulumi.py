"""Pulumi Interface - Abstraction layer for Pulumi SDK operations"""

import os
from typing import Dict, Any, Optional, Union
import pulumi
from pipeline_orchestrator.interfaces.testing import MockResource, MockStackReference
import logging

class ResourceOptions:
    """Resource options abstraction to avoid direct Pulumi SDK usage"""
    def __init__(
        self,
        parent: Optional[Union['MockResource', pulumi.Resource]] = None,
        depends_on: Optional[list[Union['MockResource', pulumi.Resource]]] = None,
        protect: bool = False
    ):
        self.parent = parent
        self.depends_on = depends_on or []
        self.protect = protect
        
    def to_pulumi_options(self) -> pulumi.ResourceOptions:
        """Convert to Pulumi ResourceOptions"""
        return pulumi.ResourceOptions(
            parent=self.parent,
            depends_on=self.depends_on,
            protect=self.protect
        )

class PulumiInterface:
    """Interface for interacting with Pulumi SDK
    
    This provides a clean abstraction over Pulumi operations, ensuring
    the rest of the application never directly uses the Pulumi SDK.
    """
    
    def __init__(self, mock_mode: bool = False):
        """Initialize Pulumi interface
        
        Args:
            mock_mode: If True, operate in mock mode without actual Pulumi SDK calls
        """
        self.mock_mode = mock_mode
        self.mock_outputs: Dict[str, Any] = {}
        self.mock_stack: Optional[MockResource] = None
        self.mock_resources: Dict[str, MockResource] = {}
        self.root_stack: Optional[Union[MockResource, pulumi.Resource]] = None
        self.logger = logging.getLogger("pipeline.pulumi")
        
        if not mock_mode:
            # In real mode, we don't create the root stack - Pulumi manages it
            self._stack_name = pulumi.get_stack()
            self._config = pulumi.Config()
            # We don't need to get the root stack in real mode
            self.root_stack = None
            self.logger.info(
                f"Initialized in real mode: stack={self._stack_name}"
            )
        else:
            self._stack_name = "mock-stack"
            self._config = None
            # Create mock stack in mock mode
            self.mock_stack = MockResource(
                "pulumi:stack:Stack",
                self._stack_name,
                {'mock': True, 'name': self._stack_name},
                pulumi.ResourceOptions(protect=True)
            )
            self.root_stack = self.mock_stack
            # Track root stack
            self.mock_resources[self._stack_name] = self.mock_stack
            self.mock_resources[f"urn:mock:pulumi:stack:Stack::{self._stack_name}"] = self.mock_stack
            self.logger.info(
                f"Initialized in mock mode: stack={self._stack_name} "
                f"mock_stack={self.mock_stack}"
            )
            
    @property
    def stack_name(self) -> str:
        """Get current stack name"""
        return self._stack_name
        
    def get_pipeline_config(self) -> Dict[str, Any]:
        """Get pipeline configuration for current stack
        
        Priority order:
        1. Environment variable PIPELINE_CONFIG
        2. Pulumi config core:pipeline_config
        3. Default example_pipeline.yaml
        """
        # First check environment variable
        env_config = os.getenv('PIPELINE_CONFIG')
        if env_config:
            return {
                'stack_name': self.stack_name,
                'pipeline_config': env_config
            }
            
        # If in mock mode, return default
        if self.mock_mode:
            return {
                'stack_name': self.stack_name,
                'pipeline_config': 'example_pipeline.yaml'
            }
            
        # Get core configuration from Pulumi
        try:
            core_config = pulumi.Config('core')
            pipeline_config = core_config.require('pipeline_config')
        except Exception:
            # Fallback to default if no Pulumi config
            pipeline_config = 'example_pipeline.yaml'
            
        return {
            'stack_name': self.stack_name,
            'pipeline_config': pipeline_config
        }
        
    def create_component_resource(
        self,
        resource_type: str,
        name: str,
        props: Optional[Dict[str, Any]] = None,
        opts: Optional[ResourceOptions] = None
    ) -> Union[MockResource, pulumi.ComponentResource]:
        """Create a new component resource
        
        Args:
            resource_type: Type of resource to create
            name: Name of resource
            props: Resource properties
            opts: Resource options
        """
        self.logger.info(f"Creating component resource: type={resource_type} name={name}")
        self.logger.debug(f"Resource properties: {props}")
        
        pulumi_opts = opts.to_pulumi_options() if opts else pulumi.ResourceOptions()
        self.logger.debug(f"Resource options: parent={pulumi_opts.parent} protect={pulumi_opts.protect}")
        
        # Only set default parent in mock mode
        if self.mock_mode and pulumi_opts.parent is None and not resource_type.startswith("pulumi:stack:"):
            pulumi_opts.parent = self.root_stack
            self.logger.info(
                f"Setting default parent for {name}: parent={self.root_stack}"
            )
        
        if self.mock_mode:
            # Create and track mock resource
            mock_resource = MockResource(resource_type, name, props or {}, pulumi_opts)
            
            # Track by URN for proper hierarchy
            self.mock_resources[mock_resource.urn] = mock_resource
            
            # Also track by name for backward compatibility
            self.mock_resources[name] = mock_resource
            
            self.logger.info(
                f"Created mock resource: type={resource_type} name={name} "
                f"urn={mock_resource.urn}"
            )
            self.logger.debug(f"Mock resource parent hierarchy: {mock_resource.parent}")
            
            return mock_resource
            
        # Create real Pulumi resource with proper registration
        self.logger.info(
            f"Creating real Pulumi resource: type={resource_type} name={name}"
        )
        
        try:
            # First register the resource with Pulumi
            resource = pulumi.ComponentResource(
                resource_type,
                name,
                props or {},
                pulumi_opts
            )
            
            self.logger.info(
                f"Created Pulumi resource: type={resource_type} name={name} "
                f"urn={getattr(resource, 'urn', None)}"
            )
            
            # Register all props as outputs to ensure they're tracked
            if props:
                self.logger.debug(f"Registering resource properties: {list(props.keys())}")
                for key, value in props.items():
                    try:
                        output = pulumi.Output.from_input(value)
                        setattr(resource, key, output)
                        self.logger.debug(f"Registered property {key} for {name}")
                    except Exception as e:
                        self.logger.error(f"Failed to register property {key} for {name}: {e}")
            
            # Register resource outputs using the resource's register_outputs method
            resource.register_outputs(props or {})
            self.logger.info(f"Successfully registered resource outputs: {name}")
            
            return resource
            
        except Exception as e:
            self.logger.error(f"Failed to create Pulumi resource {name}: {e}", exc_info=True)
            raise
        
    def export_value(
        self, 
        name: str, 
        value: Any,
        opts: Optional[ResourceOptions] = None
    ) -> None:
        """Export a stack output value
        
        Args:
            name: Name of output
            value: Value to export
            opts: Resource options for export (ignored in real mode)
        """
        if self.mock_mode:
            if not self.mock_stack:
                raise RuntimeError("No mock stack available for export")
            self.mock_outputs[name] = value
            self.mock_stack.export(name, value)
        else:
            # In real mode, we just use pulumi.export which doesn't take options
            pulumi.export(name, value)
        
    def get_stack_reference(self, stack_name: str) -> pulumi.StackReference:
        """Get a reference to another stack"""
        if self.mock_mode:
            return MockStackReference(stack_name)
            
        return pulumi.StackReference(stack_name)
        
    def get_mock_resource(self, name: str) -> Optional[MockResource]:
        """Get a mock resource by name (mock mode only)"""
        return self.mock_resources.get(name)
        
    def get_resource_tree(self) -> Dict[str, Any]:
        """Get the full resource tree in mock mode
        
        Returns a dictionary representing the resource hierarchy
        """
        if not self.mock_mode or not self.mock_stack:
            return {}
            
        def build_tree(resource: MockResource) -> Dict[str, Any]:
            return {
                'type': resource.resource_type,
                'name': resource.name,
                'props': resource.props,
                'urn': resource.urn,
                'children': [build_tree(child) for child in resource.get_children()]
            }
            
        return build_tree(self.mock_stack)