"""Resource Helper

Utilities for downloading and managing remote resources.
"""
from typing import Optional
from pathlib import Path
import urllib.request

from pipeline_orchestrator.helpers.models import AuthConfig

class ResourceDownloader:
    """Downloads resources from various sources"""
    
    @staticmethod
    def download(location: str, target: Path, auth: Optional[AuthConfig] = None) -> Path:
        """Download a resource from URL or git to specified target path
        
        Args:
            location: Resource location (URL, git URL, or local path)
            target: Path where to save the downloaded resource
            auth: Optional authentication configuration
            
        Returns:
            Path to downloaded resource (same as target)
        """
        if location.startswith(('http://', 'https://')):
            request = urllib.request.Request(location)
            if auth and auth.headers:
                for key, value in auth.headers.items():
                    request.add_header(key, value)
                    
            with urllib.request.urlopen(request) as response:
                target.write_bytes(response.read())
                return target
                    
        elif location.startswith('git@'):
            # TODO: Implement git clone with auth support
            raise NotImplementedError("Git support not implemented yet")
            
        return Path(location)