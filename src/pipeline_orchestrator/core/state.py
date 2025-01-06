"""State Management for Pipeline

Responsible for:
1. Managing global pipeline state
2. Handling cross-extension data references
3. Managing secret references
4. Tracking execution progress
"""

import logging
from typing import Dict, Any, Optional
import re

class PipelineState:
    """Manages global pipeline state and cross-extension data"""
    
    # Regex patterns for reference resolution
    GROUP_REF_PATTERN = re.compile(r'_group:(\w+):(\w+):(\w+)(?::(\w+))?')
    SECRET_REF_PATTERN = re.compile(r'_secret:(\w+):(\w+)')
    
    def __init__(self):
        self.logger = logging.getLogger("pipeline.state")
        self.execution_state: Dict[str, str] = {}  # Extension execution states
        self.extension_data: Dict[str, Dict[str, Any]] = {}  # Data produced by extensions
        self.secrets: Dict[str, Dict[str, Any]] = {}  # Loaded secrets
        
    def set_extension_state(self, extension_name: str, state: str) -> None:
        """Set execution state for an extension"""
        self.execution_state[extension_name] = state
        self.logger.debug(f"Extension {extension_name} state changed to: {state}")
        
    def get_extension_state(self, extension_name: str) -> Optional[str]:
        """Get execution state for an extension"""
        state = self.execution_state.get(extension_name)
        if state is None:
            self.logger.warning(f"No state found for extension: {extension_name}")
        return state
        
    def store_extension_data(self, extension_name: str, data: Dict[str, Any]) -> None:
        """Store data produced by an extension"""
        self.extension_data[extension_name] = data
        self.logger.debug(f"Stored data for extension: {extension_name}")

    def get_extension_data(self, extension_name: str) -> Optional[Dict[str, Any]]:
        """Get data produced by an extension
        
        Args:
            extension_name: Name of the extension
            
        Returns:
            Extension data if found, None otherwise
        """
        data = self.extension_data.get(extension_name)
        if data is None:
            self.logger.warning(f"No data found for extension: {extension_name}")
        return data

    def get_all_extension_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all extension data
        
        Returns:
            Dictionary mapping extension names to their data
        """
        return self.extension_data.copy()
        
    def resolve_group_reference(self, reference: str) -> Any:
        """Resolve a group reference (e.g., _group:terraform:proxmox:master)"""
        match = self.GROUP_REF_PATTERN.match(reference)
        if not match:
            return reference
            
        ext_name, run_name, group_name, node_name = match.groups()
        ext_data = self.extension_data.get(ext_name, {})
        group_data = ext_data.get(f"{run_name}.{group_name}")
        
        if not group_data:
            self.logger.warning(f"Could not resolve group reference: {reference}")
            return None
            
        if node_name:
            node_data = group_data.get(node_name)
            if node_data is None:
                self.logger.warning(f"Node {node_name} not found in group: {reference}")
            return node_data
        return group_data
        
    def resolve_secret_reference(self, reference: str) -> Any:
        """Resolve a secret reference (e.g., _secret:vault:api_key)"""
        match = self.SECRET_REF_PATTERN.match(reference)
        if not match:
            return reference
            
        vault_name, secret_key = match.groups()
        vault = self.secrets.get(vault_name, {})
        secret = vault.get(secret_key)
        
        if secret is None:
            self.logger.warning(f"Could not resolve secret reference: {reference}")
            
        return secret
        
    def resolve_references(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve all references in a configuration"""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, dict):
                resolved[key] = self.resolve_references(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_references(item) if isinstance(item, dict)
                    else self.resolve_secret_reference(item) if isinstance(item, str) and item.startswith('_secret:')
                    else self.resolve_group_reference(item) if isinstance(item, str) and item.startswith('_group:')
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                if value.startswith('_secret:'):
                    resolved[key] = self.resolve_secret_reference(value)
                elif value.startswith('_group:'):
                    resolved[key] = self.resolve_group_reference(value)
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
                
        return resolved
        
    def load_secrets(self, secrets_config: Dict[str, Any]) -> None:
        """Load secrets from configuration
        
        This is a placeholder - in reality, this would securely load secrets
        from files, vault, or other secure storage
        """
        self.logger.info("Loading secrets from configuration")
        # TODO: Implement secure secret loading 