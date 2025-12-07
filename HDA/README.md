# ComfyUI Bridge HDA - Complete Setup

## File Structure

```
/home/maxborg/houdini-comfy-bridge/
├── hda_interface.py          ← Main interface code (edit this)
└── scripts/
    └── hda_execute_workflow.py   ← Your execution script
```

## Installation

### 1. Copy hda_interface.py to your project
```bash
# Make sure directory exists
mkdir -p /home/maxborg/houdini-comfy-bridge

# Copy the file
cp hda_interface.py /home/maxborg/houdini-comfy-bridge/
```

### 2. Update your HDA's PythonModule
1. Open your HDA in Houdini
2. Right-click → Type Properties
3. Go to Scripts tab → PythonModule
4. Delete everything in there
5. Copy and paste the entire content of `PythonModule.py`
6. Click Accept

### 3. Make sure your HDA has these parameters

Your DialogScript should have at least:
- `workflow_path` (file parameter)
- `workflow_info` (label parameter)
- `input_mapping` (label parameter) 
- `server_address` (string parameter)
- `server_port` (integer parameter)
- `connection_status` (label parameter)
- `output_path` (directory parameter)
- `verbose` (toggle parameter)
- `execute` (button parameter)

### 4. Set up callbacks

**For workflow_path parameter:**
```
script_callback: hou.phm().on_workflow_changed(kwargs['node'])
script_callback_language: python
```

**For execute button:**
```
script_callback: hou.phm().execute_workflow(kwargs['node'])
script_callback_language: python
```

**For test connection button:**
```
script_callback: hou.phm().test_connection(kwargs['node'])
script_callback_language: python
```

## How It Works

1. **Load workflow:** Set workflow_path → automatically detects INPUT_ nodes
2. **Connect inputs:** Connect COP nodes to input0, input1, etc.
3. **Execute:** Click Execute button → calls your hda_execute_workflow.py

## Workflow Format

Your ComfyUI workflow needs LoadImage nodes with titles starting with `INPUT_`:

```json
{
  "1": {
    "class_type": "LoadImage",
    "_meta": {
      "title": "INPUT_source_image"
    }
  }
}
```

This becomes `input0` in Houdini.

## Available Functions

From your hda_execute_workflow.py, you can access:

```python
import hou

# Get workflow input mapping
inputs = hou.phm().get_workflow_inputs(node)
# Returns: [{'node_id': '1', 'name': 'source_image', ...}, ...]

# Get workflow JSON
workflow = hou.phm().get_workflow_json(node)

# Get server URL
url = hou.phm().get_server_url(node)
# Returns: "http://127.0.0.1:8188"

# Get output directory
output_dir = hou.phm().get_output_directory(node)
# Returns: expanded path, creates if needed
```

## Editing Code

Just edit `/home/maxborg/houdini-comfy-bridge/hda_interface.py` in your text editor.

Changes are picked up automatically on next execution (the PythonModule reloads it).

No need to rebuild the HDA!

## Troubleshooting

**Nothing happens when clicking Execute:**
1. Check Python Shell for errors
2. Make sure hda_interface.py exists in the right location
3. Make sure the PythonModule is updated

**"Could not import execution module":**
- Check that `/home/maxborg/houdini-comfy-bridge/scripts/hda_execute_workflow.py` exists

**"No INPUT_ nodes found":**
- Open your workflow in ComfyUI
- Rename LoadImage nodes to start with `INPUT_`
- Save the workflow JSON

## Files Included

- `PythonModule.py` - Copy into HDA's PythonModule section
- `hda_interface.py` - Copy to /home/maxborg/houdini-comfy-bridge/
- `README.md` - This file
