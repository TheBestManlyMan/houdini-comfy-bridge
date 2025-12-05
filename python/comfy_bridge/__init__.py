"""
Houdini-ComfyUI Bridge
A bridge for integrating ComfyUI workflows into Houdini COPs.
"""

from .comfy_api import ComfyAPI
from .comfy_parser import ComfyWorkflowParser

__version__ = "0.1.0"
__all__ = ["ComfyAPI", "ComfyWorkflowParser"]
