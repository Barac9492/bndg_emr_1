"""
logger.py — Centralized logging configuration
"""

import logging
import sys
from typing import Optional

from config import get_settings


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Setup structured logger with proper formatting."""
    settings = get_settings()
    
    if level is None:
        level = logging.DEBUG if settings.enable_debug else logging.INFO
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger