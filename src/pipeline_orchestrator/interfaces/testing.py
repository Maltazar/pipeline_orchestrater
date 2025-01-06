"""Testing utilities for Pulumi interface

Provides mock implementations of Pulumi resources for testing.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import logging
from pulumi import ResourceOptions

@dataclass
class MockResource:
    """Mock implementation of Pulumi ComponentResource"""
    resource_type: str
    name: str
    props: Dict[str, Any]
    opts: Optional[ResourceOptions] = None
    _is_stack: bool = field(init=False, default=False)
    _outputs: Dict[str, Any] = field(default_factory=dict)
    _children: List['MockResource'] = field(default_factory=list)
    _urn: str = field(init=False)
    _logger: logging.Logger = field(init=False)

    def __post_init__(self):
        """Initialize instance variables"""
        self._is_stack = self.resource_type == "pulumi:stack:Stack"
        self._urn = f"urn:mock:{self.resource_type}::{self.name}"
        self._logger = logging.getLogger("mock.resources")
        
        # If we have a parent, add ourselves as their child
        if self.opts and self.opts.parent:
            parent = self.opts.parent
            if isinstance(parent, MockResource):
                parent.add_child(self)
            else:
                self._logger.warning(
                    f"Parent of {self.resource_type}:{self.name} is not a MockResource"
                )
                
    def add_child(self, child: 'MockResource') -> None:
        """Add a child resource
        
        This is the single point of truth for managing parent-child relationships.
        """
        self._logger.debug(
            f"Adding child {child.resource_type}:{child.name} to "
            f"{self.resource_type}:{self.name}"
        )
        if child not in self._children:
            self._children.append(child)

    def is_stack(self) -> bool:
        """Check if this is a stack resource"""
        return self._is_stack

    def export(self, name: str, value: Any) -> None:
        """Mock implementation of stack export"""
        if not self.is_stack():
            raise Exception("Failed to export output. Root resource is not an instance of 'Stack'")
        self._outputs[name] = value

    def get_output(self, name: str) -> Any:
        """Get an exported stack output"""
        return self._outputs.get(name)
        
    def get_children(self) -> List['MockResource']:
        """Get child resources"""
        return self._children
        
    @property
    def urn(self) -> str:
        """Get the URN for this resource"""
        return self._urn
        
    @property
    def parent(self) -> Optional['MockResource']:
        """Get the parent resource"""
        if self.opts and self.opts.parent:
            return self.opts.parent if isinstance(self.opts.parent, MockResource) else None
        return None

    def __str__(self) -> str:
        return f"MockResource({self.resource_type}:{self.name})"

@dataclass
class MockStackReference:
    """Mock implementation of Pulumi StackReference"""
    name: str
    outputs: Dict[str, Any] = field(default_factory=dict)

    def get_output(self, key: str) -> Any:
        """Mock implementation of get_output"""
        return self.outputs.get(key)

    def __str__(self) -> str:
        return f"MockStackReference({self.name})" 