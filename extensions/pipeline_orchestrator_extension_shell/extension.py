"""Shell Extension Implementation

Implements shell command execution functionality.
"""
from typing import Dict, Any, Optional, List
import subprocess
import tempfile
from pathlib import Path

from pipeline_orchestrator.handlers.extension import ExtensionHandler
from pipeline_orchestrator.helpers.resources import ResourceDownloader
from pipeline_orchestrator.helpers.containers import ContainerRunner
from .models import ShellConfig

class ShellExtension(ExtensionHandler):
    """Shell extension for executing shell commands and scripts
    
    Supports:
    - Direct command execution
    - Script execution from file/URL/git
    - Host or container isolation
    """
    
    def __init__(self):
        super().__init__()
        self.configs: Optional[List[ShellConfig]] = []
    
    def execute_command(self, config: ShellConfig, command: str) -> None:
        """Execute a shell command
        
        Args:
            config: Shell configuration for this command
            command: Command to execute
        """
        # Create command resource with proper naming
        command_name = f"command.{config.name}.{hash(command) & 0xFFFFFFFF:08x}"
        command_resource = self.create_resource(
            f'shell:command:{config.name}',
            command_name,
            props={
                'command': command,
                'shell_type': config.type,
                'isolation': config.isolation.model_dump() if config.isolation else None,
                'config_name': config.name
            }
        )
        
        try:
            # Execute in container if isolation is configured
            if config.isolation and config.isolation.type == "container":
                result = ContainerRunner.run(
                    command,
                    config.isolation.base_image or "ubuntu:22.04"
                )
            else:
                # Execute on host
                result = subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True
                )
            
            # Store and export command output
            output_data = {
                'command': command,
                'output': result.stdout.strip(),
                'exit_code': result.returncode
            }
            self.export_output(f'{config.name}_output', output_data, command_resource)
            
        except subprocess.CalledProcessError as e:
            # Store and export error data
            error_data = {
                'command': command,
                'error': e.stderr,
                'exit_code': e.returncode
            }
            self.export_output(f'{config.name}_error', error_data, command_resource)
            raise
    
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate shell extension configuration
        
        Args:
            config: Raw configuration dictionary
        """
        self.logger.info(f"Validating shell extension configuration: {config}")
        
        # Config should be a dictionary of shell configurations
        if not isinstance(config, dict):
            raise ValueError("Shell extension configuration must be a dictionary")
            
        # Validate each configuration
        self.configs = []
        for name, item in config.items():
            # Add name to config if not present
            if 'name' not in item:
                item['name'] = name
            
            shell_config = ShellConfig(**item)
            shell_config.validate_config()
            self.configs.append(shell_config)
            
    def execute(self, config: Dict[str, Any]) -> None:
        """Execute shell commands or scripts
        
        Args:
            config: Configuration dictionary
        """
        self.validate_config(config)
        
        if not self.configs:
            raise RuntimeError("No valid configurations found")
        
        # Execute each configuration
        for config in self.configs:
            # Execute direct commands
            if config.commands:
                for command in config.commands:
                    self.execute_command(config, command)
                    
            # Execute scripts
            if config.scripts:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    for script in config.scripts:
                        # Create target directory structure if needed
                        target_path = temp_path / script.file
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Download script with auth if configured
                        downloaded_path = ResourceDownloader.download(
                            script.location,
                            target=target_path,
                            auth=script.auth
                        )
                        self.execute_command(config, f"{script.type} {downloaded_path}") 