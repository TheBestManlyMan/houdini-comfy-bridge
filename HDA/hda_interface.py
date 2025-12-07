"""
hda_interface.py
ComfyUI Bridge HDA Interface

This module handles all the UI callbacks and workflow parsing for the
ComfyUI Bridge HDA.

Author: Max
"""

import hou
import json
import os
import sys
import urllib.request
import urllib.error


# Dynamically determine scripts directory
def _get_scripts_dir():
    """Find the scripts directory dynamically."""
    # Method 1: Check environment variable
    if 'COMFY_BRIDGE_ROOT' in os.environ:
        return os.path.join(os.environ['COMFY_BRIDGE_ROOT'], 'scripts')

    # Method 2: Relative to this file (HDA/hda_interface.py -> ../scripts/)
    this_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(this_file))
    scripts_dir = os.path.join(project_root, 'scripts')
    if os.path.exists(scripts_dir):
        return scripts_dir

    # Method 3: Check PYTHONPATH entries
    for path in sys.path:
        potential_scripts = os.path.join(path, 'scripts')
        if os.path.exists(potential_scripts):
            hda_exec = os.path.join(potential_scripts, 'hda_execute_workflow.py')
            if os.path.exists(hda_exec):
                return potential_scripts

    # Method 4: Fallback to common installation location
    default_path = os.path.expanduser('~/houdini-comfy-bridge/scripts')
    if os.path.exists(default_path):
        return default_path

    # Last resort - raise error with helpful message
    raise RuntimeError(
        "Could not locate houdini-comfy-bridge scripts directory!\n\n"
        "Tried:\n"
        "  1. COMFY_BRIDGE_ROOT environment variable\n"
        "  2. Relative to HDA file location\n"
        "  3. PYTHONPATH entries\n"
        "  4. ~/houdini-comfy-bridge/scripts\n\n"
        "Solutions:\n"
        "  - Set COMFY_BRIDGE_ROOT environment variable to project root\n"
        "  - Or ensure scripts are in your PYTHONPATH\n"
        "  - Or install to ~/houdini-comfy-bridge/"
    )

SCRIPTS_DIR = _get_scripts_dir()
MAX_INPUTS = 10


def get_workflow_inputs(node):
    """
    Parse workflow JSON and find all INPUT_ nodes.
    
    Returns a list of dicts with:
        - node_id: ComfyUI node ID
        - name: Display name (without INPUT_ prefix)
        - class_type: Node type (e.g. 'LoadImage')
        - input_key: Safe identifier for the input
        - original_title: Full title from workflow
    """
    workflow_path = node.parm('workflow_path').evalAsString()
    if not workflow_path:
        return []

    workflow_path = hou.text.expandString(workflow_path)
    if not os.path.exists(workflow_path):
        return []
    
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading workflow: {e}")
        return []
    
    inputs = []
    for node_id, node_data in workflow.items():
        if not isinstance(node_data, dict):
            continue
        
        meta = node_data.get('_meta')
        if not meta or not isinstance(meta, dict):
            continue
        
        title = meta.get('title', '')
        if title.startswith('INPUT_'):
            inputs.append({
                'node_id': node_id,
                'name': title[6:],
                'class_type': node_data.get('class_type', 'Unknown'),
                'input_key': title[6:].lower().replace(' ', '_'),
                'original_title': title
            })
    
    inputs.sort(key=lambda x: int(x['node_id']))
    return inputs


def get_workflow_json(node):
    """Load and return the workflow as a dict."""
    workflow_path = node.parm('workflow_path').evalAsString()
    workflow_path = hou.text.expandString(workflow_path)

    if not os.path.exists(workflow_path):
        return None
    
    try:
        with open(workflow_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading workflow: {e}")
        return None


def on_workflow_changed(node):
    """
    Callback when workflow file changes.
    Scans for INPUT_ nodes and updates the UI.
    """
    inputs = get_workflow_inputs(node)
    
    if not inputs:
        _show_no_inputs_found(node)
        return
    
    if len(inputs) > MAX_INPUTS:
        print(f"WARNING: Workflow needs {len(inputs)} inputs but HDA only has {MAX_INPUTS}")
    
    info_lines = [f"Found {len(inputs)} inputs:"]
    mapping_lines = ["Houdini Input → ComfyUI Node"]
    
    for i, inp in enumerate(inputs):
        info_lines.append(f"  [{i}] {inp['name']} ({inp['class_type']})")
        mapping_lines.append(f"  input{i} → {inp['original_title']} (node {inp['node_id']})")
    
    info_parm = node.parm('workflow_info')
    if info_parm:
        info_parm.set('\n'.join(info_lines))
    
    mapping_parm = node.parm('input_mapping')
    if mapping_parm:
        mapping_parm.set('\n'.join(mapping_lines))
    
    node.setUserData('workflow_inputs', json.dumps(inputs))
    
    print("=" * 60)
    print("Workflow loaded successfully")
    for i, inp in enumerate(inputs):
        print(f"  input{i} → {inp['name']} (node {inp['node_id']})")
    print("=" * 60)
    
    hou.ui.displayMessage(
        f"Successfully loaded workflow!\n\n"
        f"Found {len(inputs)} INPUT_ nodes:\n" + 
        "\n".join([f"  input{i} → {inp['name']}" for i, inp in enumerate(inputs)]),
        severity=hou.severityType.Message,
        title="Workflow Loaded"
    )


def _show_no_inputs_found(node):
    """Helper to show warning when no INPUT_ nodes found."""
    info_parm = node.parm('workflow_info')
    if info_parm:
        info_parm.set("No INPUT_ nodes found")
    
    mapping_parm = node.parm('input_mapping')
    if mapping_parm:
        mapping_parm.set("")
    
    node.setUserData('workflow_inputs', '')
    
    hou.ui.displayMessage(
        "No INPUT_ nodes found in workflow!\n\n"
        "To add inputs:\n"
        "1. Open workflow in ComfyUI\n"
        "2. Rename LoadImage nodes to start with INPUT_\n"
        "   Example: INPUT_source_image\n"
        "3. Save the workflow\n"
        "4. Reload in Houdini",
        severity=hou.severityType.Warning,
        title="No Inputs Found"
    )


def test_connection(node):
    """Test connection to ComfyUI server."""
    server = node.parm('server_address').evalAsString()
    port = node.parm('server_port').eval()
    url = f"http://{server}:{port}/system_stats"
    
    status_parm = node.parm('connection_status')
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            os_name = data.get('system', {}).get('os', 'Unknown')
            
            status_parm.set(f"✓ Connected - {os_name}")
            
            hou.ui.displayMessage(
                f"Successfully connected!\n\n"
                f"Server: {server}:{port}\n"
                f"System: {os_name}",
                severity=hou.severityType.Message
            )
            return True
            
    except urllib.error.URLError as e:
        status_parm.set(f"✗ Connection failed")
        
        hou.ui.displayMessage(
            f"Failed to connect to ComfyUI\n\n"
            f"Server: {server}:{port}\n"
            f"Error: {e.reason}\n\n"
            f"Make sure ComfyUI is running.",
            severity=hou.severityType.Error
        )
        return False
        
    except Exception as e:
        status_parm.set(f"✗ Error: {str(e)}")
        hou.ui.displayMessage(
            f"Connection error:\n\n{str(e)}",
            severity=hou.severityType.Error
        )
        return False


def execute_workflow(node):
    """
    Main execution function.
    Validates everything then calls the external execution script.
    """
    workflow_path = node.parm('workflow_path').evalAsString()
    if not workflow_path:
        _show_error(node, "No workflow file specified")
        return

    workflow_path = hou.text.expandString(workflow_path)
    if not os.path.exists(workflow_path):
        _show_error(node, f"Workflow file not found:\n{workflow_path}")
        return
    
    inputs = get_workflow_inputs(node)
    if not inputs:
        _show_error(node, "No INPUT_ nodes found in workflow")
        return
    
    missing = []
    for i, inp in enumerate(inputs):
        if not node.input(i):
            missing.append(f"  input{i} ({inp['name']})")
    
    if missing:
        _show_error(node, "These inputs are not connected:\n\n" + "\n".join(missing))
        return
    
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)

    # Clear module cache if verbose mode is enabled (parameter may not exist)
    verbose_parm = node.parm('verbose')
    if verbose_parm and verbose_parm.eval():
        _clear_module_cache()
    
    try:
        import hda_execute_workflow
        
        print("\n" + "=" * 70)
        print("Executing ComfyUI workflow")
        print("=" * 70)
        
        for i, inp in enumerate(inputs):
            source = node.input(i)
            print(f"  input{i}: {inp['name']} ← {source.path()}")
        
        print("-" * 70)
        
        hda_execute_workflow.execute_workflow(node)
        
        print("-" * 70)
        print("Execution completed successfully")
        print("=" * 70 + "\n")
        
    except ImportError as e:
        _show_error(node, f"Could not import execution module:\n\n{e}\n\nMake sure {SCRIPTS_DIR}/hda_execute_workflow.py exists")
        raise
        
    except Exception as e:
        _show_error(node, f"Execution error:\n\n{type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def _show_error(node, message):
    """Helper to show error messages."""
    print(f"ERROR: {message}")
    hou.ui.displayMessage(message, severity=hou.severityType.Error)


def _clear_module_cache():
    """Clear cached Python modules related to ComfyUI bridge."""
    keywords = ['comfy', 'hda_execute', 'workflow', 'bridge']
    cleared = [k for k in list(sys.modules.keys()) 
               if any(word in k.lower() for word in keywords)]
    
    for module in cleared:
        del sys.modules[module]
    
    if cleared:
        print(f"Cleared {len(cleared)} cached modules")


def get_server_url(node):
    """Get the full ComfyUI server URL."""
    server = node.parm('server_address').evalAsString()
    port = node.parm('server_port').eval()
    return f"http://{server}:{port}"


def get_output_directory(node):
    """Get output directory, creating it if needed."""
    output_path = node.parm('output_path').evalAsString()
    output_path = hou.text.expandString(output_path)

    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)

    return output_path
