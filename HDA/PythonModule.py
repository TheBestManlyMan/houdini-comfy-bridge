"""
ComfyUI Bridge HDA - PythonModule

This is the code that goes inside the HDA's PythonModule section.
It's a simple loader that imports everything from hda_interface.py

Copy this entire file content into:
HDA Type Properties → Scripts → PythonModule
"""

import sys
import os
import hou

# Dynamically determine project directory based on HDA location
# Try multiple methods to find the correct path
def _get_project_dir():
    """Find the project directory dynamically."""
    # Method 1: Check for environment variable
    if 'COMFY_BRIDGE_ROOT' in os.environ:
        return os.environ['COMFY_BRIDGE_ROOT']

    # Method 2: Use houdini.env PYTHONPATH (already in sys.path)
    for path in sys.path:
        hda_dir = os.path.join(path, 'HDA')
        if os.path.exists(hda_dir) and os.path.exists(os.path.join(hda_dir, 'hda_interface.py')):
            return path

    # Method 3: Fallback to default location (works for development)
    default_path = os.path.expanduser('~/houdini-comfy-bridge')
    if os.path.exists(default_path):
        return default_path

    # Method 4: Last resort - hardcoded (but warn user)
    print("WARNING: Using hardcoded path. Please set COMFY_BRIDGE_ROOT environment variable.")
    return '/home/maxborg/houdini-comfy-bridge'

PROJECT_DIR = _get_project_dir()
HDA_DIR = os.path.join(PROJECT_DIR, 'HDA')

# Add both project root and HDA directory to path
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
if HDA_DIR not in sys.path:
    sys.path.insert(0, HDA_DIR)

try:
    # Reload module to pick up code changes
    if 'hda_interface' in sys.modules:
        import importlib
        import hda_interface
        importlib.reload(hda_interface)
    else:
        import hda_interface

    # Import all public functions
    from hda_interface import (
        get_workflow_inputs,
        get_workflow_json,
        on_workflow_changed,
        test_connection,
        execute_workflow,
        get_server_url,
        get_output_directory
    )
    
except ImportError as e:
    print(f"ERROR: Could not load hda_interface module: {e}")
    print(f"Make sure {PROJECT_DIR}/hda_interface.py exists")
    
    # Provide stub functions to prevent errors
    def get_workflow_inputs(node): return []
    def get_workflow_json(node): return None
    def on_workflow_changed(node): pass
    def test_connection(node): return False
    def execute_workflow(node): pass
    def get_server_url(node): return ""
    def get_output_directory(node): return ""
