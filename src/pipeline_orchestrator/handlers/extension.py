"""Extension Handler Interface

Responsible for:
1. Extension-specific validation
2. Container operations
3. Isolated state and resources
4. Extension lifecycle methods
5. Extension-specific cleanup
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from pipeline_orchestrator.interfaces.pulumi import PulumiInterface, ResourceOptions

class ExtensionHandler(ABC):
    """Base class for all extension handlers
    
    Provides minimal interface requirements for extensions.
    Each extension is responsible for:
    1. Implementing its own validation logic
    2. Managing its own state and resources
    3. Handling its own execution flow
    4. Cleaning up its resources
    """
    
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}
        self.pulumi: Optional[PulumiInterface] = None
        self.name: Optional[str] = None
        self.parent_stack_name: Optional[str] = None
        self.stack_name: Optional[str] = None
        self.stack_resource: Optional[Any] = None
        self.logger: Optional[logging.Logger] = None
        
    def initialize(self, name: str, parent_stack_name: str, pulumi: PulumiInterface) -> None:
        """Initialize the extension with required context
        
        Args:
            name: Extension name from configuration
            parent_stack_name: Parent stack name from pulumi up
            pulumi: Pulumi interface instance
        """
        self.name = name
        self.parent_stack_name = parent_stack_name
        self.pulumi = pulumi
        
        # Get logger and inherit level from root logger
        root_logger = logging.getLogger("pipeline")
        self.logger = logging.getLogger(f"extensions.{name}")

        # Set level and ensure propagation
        self.logger.setLevel(root_logger.level)
        self.logger.parent = root_logger  # Explicitly set parent logger
        self.logger.propagate = True
        
        # Create extension-specific stack name
        self.stack_name = f"{self.parent_stack_name}.{self.name}"
        
        # Create stack resource with proper naming
        extension_type = f'pipeline:extension:{self.name}'
        self.stack_resource = pulumi.create_component_resource(
            extension_type,
            self.stack_name,
            props={
                'name': self.name,
                'parent_stack': self.parent_stack_name,
                'type': extension_type
            },
            opts=ResourceOptions(
                parent=pulumi.mock_stack if pulumi.mock_mode else pulumi.root_stack,
                protect=True  # Protect extension resources
            )
        )
            
        self.logger.info(f"Initialized extension {name} in stack {parent_stack_name}")
        
    def create_resource(
        self,
        resource_type: str,
        name: str,
        props: Optional[Dict[str, Any]] = None,
        parent: Optional[Any] = None,
        depends_on: Optional[list[Any]] = None
    ) -> Any:
        """Create a new resource with proper parent and dependencies
        
        Args:
            resource_type: Type of resource to create
            name: Name of resource
            props: Resource properties
            parent: Parent resource (defaults to stack_resource)
            depends_on: Resources this resource depends on
            
        Returns:
            Created resource
        """
        if not self.pulumi:
            raise RuntimeError("Extension not properly initialized")
            
        # Create fully qualified resource name
        resource_name = f"{self.stack_name}.{name}"
        
        # Ensure props includes type information
        full_props = {
            'type': resource_type,
            'stack': self.stack_name,
            'extension': self.name,
            'parent_resource': parent.name if parent else None,
            **(props or {})
        }
        
        # Ensure proper parent hierarchy - always set a parent
        effective_parent = parent or self.stack_resource
        if not effective_parent:
            # If no parent is set, use the root stack
            effective_parent = self.pulumi.mock_stack if self.pulumi.mock_mode else self.pulumi.root_stack
            
        # Create the resource with proper parenting
        resource = self.pulumi.create_component_resource(
            resource_type,
            resource_name,
            props=full_props,
            opts=ResourceOptions(
                parent=effective_parent,
                depends_on=depends_on,
                protect=resource_type.startswith('pipeline:extension:') # Protect extension resources
            )
        )
        
        # Log resource creation
        self.logger.debug(
            f"Created resource: type={resource_type} name={resource_name} "
            f"parent={effective_parent.name if effective_parent else None}"
        )
        
        return resource
        
    def export_output(
        self,
        name: str,
        value: Any,
        parent: Optional[Any] = None
    ) -> None:
        """Export an output value with proper resource dependencies
        
        Args:
            name: Name of output
            value: Value to export
            parent: Parent resource (defaults to stack_resource)
        """
        if not self.pulumi:
            raise RuntimeError("Extension not properly initialized")
            
        # Store in outputs for state management
        if name not in self.outputs:
            self.outputs[name] = []
        self.outputs[name].append(value)
        
        # Export via Pulumi with proper resource dependencies
        self.pulumi.export_value(
            f"{self.name}_{name}",
            value,
            opts=ResourceOptions(parent=parent or self.stack_resource)
        )
        
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate extension-specific configuration
        
        Each extension must implement its own validation logic.
        
        Args:
            config: Raw configuration dictionary from pipeline
        """
        pass
        
    @abstractmethod
    def execute(self, config: Dict[str, Any]) -> None:
        """Execute the extension with given configuration
        
        Each extension must implement its own execution logic.
        
        Args:
            config: Configuration dictionary from pipeline
        """
        pass

    def get_output_data(self) -> Dict[str, Any]:
        """Get the output data from extension execution
        
        Returns:
            Dictionary containing extension output data
        """
        return self.outputs

    def cleanup(self) -> None:
        """Cleanup extension resources
        
        Basic cleanup implementation that exports state.
        Extensions should override this if they need custom cleanup.
        """
        if self.pulumi and self.stack_name:
            # Export final state before cleanup
            self.pulumi.export_value(
                f"{self.name}_final_state",
                {
                    "state": self.state,
                    "outputs": self.outputs
                },
                opts=ResourceOptions(parent=self.stack_resource)
            )
            # Only clear Pulumi state, keep outputs intact
            self.state.clear()