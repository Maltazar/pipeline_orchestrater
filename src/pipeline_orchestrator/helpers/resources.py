"""Resource Helper

Utilities for downloading and managing remote resources.
"""
from typing import Optional
from pathlib import Path
import urllib.request
import shutil
import subprocess
import logging
from urllib.parse import urlparse

from pipeline_orchestrator.helpers.models import AuthConfig

logger = logging.getLogger(__name__)

class ResourceDownloader:
    """Downloads resources from various sources"""
    
    @staticmethod
    def download(location: str, target: Path, file: str, auth: Optional[AuthConfig] = None) -> Path:
        """Download a resource from URL, git, or copy from local path to specified target
        
        Args:
            location: Resource location (URL, git URL, or local path)
            target: Path where to save the downloaded resource
            file: Target filename
            auth: Optional authentication configuration
            
        Returns:
            Path to downloaded resource
        """
        # Parse the location URL/path
        parsed = urlparse(location)
        target_path = target / file
        
        # Handle HTTP(S) downloads
        if parsed.scheme in ('http', 'https'):
            # Only treat as git if it's explicitly a git repository URL pattern
            if location.endswith('.git'):
                return_resource = ResourceDownloader._handle_git_repo(location, target)
                return_resource = return_resource / file
            else:
                # Treat as direct file download
                return_resource = ResourceDownloader._download_http(location, target_path, auth)
                
        # Handle SSH git URLs
        elif location.startswith('git@'):
            return_resource = ResourceDownloader._handle_git_repo(location, target)
            return_resource = return_resource / file
            
        # Handle local files
        elif parsed.scheme == 'file' or not parsed.scheme:
            return_resource = ResourceDownloader._copy_local_file(location, target_path)
            
        else:
            raise ValueError(f"Unsupported location protocol: {parsed.scheme}")
        
        return return_resource

    @staticmethod
    def _download_http(url: str, target: Path, auth: Optional[AuthConfig] = None) -> Path:
        """Download file from HTTP(S) URL"""
        logger.info(f"Downloading from URL: {url} to {target}")
        request = urllib.request.Request(url)
        if auth and auth.headers:
            for key, value in auth.headers.items():
                request.add_header(key, value)
                
        with urllib.request.urlopen(request) as response:
            target.write_bytes(response.read())
        return target

    @staticmethod
    def _handle_git_repo(repo_url: str, target: Path) -> Path:
        """Handle git repository - clone if new, pull if existing"""
        logger.info(f"Handling git repository: {repo_url} at {target}")
        
        git_dir = target / '.git'
        
        if git_dir.exists():
            return ResourceDownloader._update_git_repo(target)
        else:
            return ResourceDownloader._clone_git_repo(repo_url, target)

    @staticmethod
    def _clone_git_repo(repo_url: str, target: Path) -> Path:
        """Clone new git repository"""
        logger.info(f"Cloning new git repository: {repo_url} to {target}")
        
        try:
            subprocess.run(
                ['git', 'clone', repo_url, str(target)],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            raise
            
        return target

    @staticmethod
    def _update_git_repo(target: Path) -> Path:
        """Update existing git repository"""
        logger.info(f"Updating existing git repository at {target}")
        
        try:
            # Check for uncommitted changes
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                check=True,
                capture_output=True,
                text=True,
                cwd=target
            )
            
            if result.stdout.strip():
                error_msg = "Repository has uncommitted changes. Please commit or stash them first."
                logger.error(error_msg)
                raise subprocess.CalledProcessError(
                    1, 'git status', 
                    output=result.stdout, 
                    stderr=error_msg
                )
            
            # Fetch all changes
            subprocess.run(
                ['git', 'fetch', '--all'],
                check=True,
                capture_output=True,
                text=True,
                cwd=target
            )
            
            # Get current branch name
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                check=True,
                capture_output=True,
                text=True,
                cwd=target
            )
            current_branch = result.stdout.strip()
            
            # Pull changes from current branch
            subprocess.run(
                ['git', 'pull', 'origin', current_branch],
                check=True,
                capture_output=True,
                text=True,
                cwd=target
            )
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git update failed: {e.stderr}")
            raise
            
        return target

    @staticmethod
    def _copy_local_file(source: str, target: Path) -> Path:
        """Copy local file or directory"""
        # Remove file:// prefix if present
        source = source.replace('file://', '')
        source_path = Path(source)
        
        logger.info(f"Copying local resource: {source_path} to {target}")
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")
            
        if source_path.is_dir():
            shutil.copytree(source_path, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
            
        return target
