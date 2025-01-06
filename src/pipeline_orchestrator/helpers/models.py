"""Helper Models

Common models used by helper utilities.
"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class AuthConfig:
    """Authentication configuration for remote resources"""
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None 