"""
Logging utility for Houdini-ComfyUI Bridge.

Provides consistent logging across the bridge with optional debug mode.
"""

import logging
import sys
from typing import Optional


class BridgeLogger:
    """Logging helper for ComfyUI Bridge operations."""

    def __init__(self, name: str = "comfy_bridge", debug: bool = False):
        """
        Initialize logger.

        Args:
            name: Logger name
            debug: Enable debug-level logging
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG if debug else logging.INFO)

            formatter = logging.Formatter(
                '[%(levelname)s] %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)


# Global logger instance - can be configured at module import
_default_logger: Optional[BridgeLogger] = None


def get_logger(debug: bool = False) -> BridgeLogger:
    """
    Get or create the default logger instance.

    Args:
        debug: Enable debug logging

    Returns:
        BridgeLogger instance
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = BridgeLogger(debug=debug)
    return _default_logger


def set_debug_mode(enabled: bool) -> None:
    """
    Enable or disable debug logging globally.

    Args:
        enabled: True to enable debug logs
    """
    global _default_logger
    _default_logger = BridgeLogger(debug=enabled)
