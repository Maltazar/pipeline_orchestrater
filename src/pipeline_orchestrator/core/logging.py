"""Logging System for Pipeline

Responsible for:
1. Centralized logging configuration
2. Structured logging output
3. File and console output
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime

def setup_logger(log_level: str = "INFO", log_dir: Path = Path("logs")) -> logging.Logger:
    """Configure and return the pipeline logger
    
    File logging can be disabled by setting DISABLE_FILE_LOGGING environment variable
    """
    
    # Create logger
    logger = logging.getLogger("pipeline")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (unless disabled by environment variable)
    if not os.getenv("DISABLE_FILE_LOGGING"):
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger 