"""Shell Extension Models

Defines the configuration models for the shell extension.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from pipeline_orchestrator.helpers.models import AuthConfig

class ShellIsolation(BaseModel):
    """Shell isolation configuration"""
    type: str = Field(default="host", description="Isolation type (host or container)")
    base_image: Optional[str] = Field(None, description="Base image for container isolation")

class ShellScript(BaseModel):
    """Shell script configuration"""
    file: str = Field(..., description="Script file path or URL")
    type: str = Field(..., description="Script type (bash, sh, zsh, etc)")
    location: str = Field(..., description="Script location (file path, URL, or git URL)")
    auth: Optional[AuthConfig] = None

class ShellConfig(BaseModel):
    """Shell extension configuration"""
    name: str = Field(..., description="Name of the shell command")
    type: str = Field(default="bash", description="Shell type (bash, sh, zsh, etc)")
    isolation: Optional[ShellIsolation] = Field(
        default=None, 
        description="Isolation configuration"
    )
    scripts: Optional[List[ShellScript]] = Field(
        default=None,
        description="List of scripts to execute"
    )
    commands: Optional[List[str]] = Field(
        default=None,
        description="List of shell commands to execute"
    )

    def validate_config(self) -> None:
        """Validate shell configuration
        
        Ensures either scripts or commands are provided, but not both empty.
        """
        if not self.scripts and not self.commands:
            raise ValueError("Either scripts or commands must be provided") 