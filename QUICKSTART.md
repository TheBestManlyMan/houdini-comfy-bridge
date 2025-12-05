# Quick Start Guide

Get up and running with Houdini-ComfyUI Bridge in 5 minutes!

## Prerequisites

- ✅ Houdini 19.5+ installed
- ✅ ComfyUI installed and working
- ✅ Python 3.9+ (comes with Houdini)

## 1. Start ComfyUI

```bash
cd /path/to/ComfyUI
python main.py
```

Verify ComfyUI is running at: http://127.0.0.1:8188

## 2. Install Houdini Bridge

### Option A: Environment Variables (Recommended)

Edit `~/houdini19.5/houdini.env`:

```bash
PYTHONPATH = /path/to/houdini-comfy-bridge/python:$PYTHONPATH
HOUDINI_SCRIPT_PATH = /path/to/houdini-comfy-bridge/scripts:$HOUDINI_SCRIPT_PATH
```

### Option B: Manual Python Path

In Houdini Python Shell:

```python
import sys
sys.path.append('/path/to/houdini-comfy-bridge/python')
```

## 3. Test Installation

### Test Python Modules

In Houdini Python Shell:

```python
from comfy_bridge import ComfyAPI, ComfyWorkflowParser

# Test API
api = ComfyAPI()
print(f"ComfyUI Connected: {api.is_server_alive()}")

# Test Parser
parser = ComfyWorkflowParser('/path/to/houdini-comfy-bridge/examples/example_workflow.json')
print(f"Input nodes found: {len(parser.get_input_nodes())}")
```

Expected output:
```
ComfyUI Connected: True
Input nodes found: 3
```

## 4. Create Your First Workflow

### In ComfyUI:

1. **Create a basic workflow** (or load default)
2. **Rename nodes** you want to control:
   - Right-click node → Properties
   - Change title to `INPUT_prompt` (for example)
   - Any node with `INPUT_` prefix will become editable in Houdini
3. **Save workflow**:
   - Click "Save (API Format)" button
   - Save as `my_workflow.json`

### Example INPUT nodes:

- `INPUT_prompt` → Text prompt parameter
- `INPUT_negative` → Negative prompt parameter
- `INPUT_seed` → Random seed parameter
- `INPUT_dimensions` → Width/height parameters

## 5. Use in Houdini

### Method 1: Python Node (Quickest)

1. Create `/img` (COP context)
2. Create Python COP node
3. Paste this code:

```python
import sys
import os
sys.path.insert(0, '/path/to/houdini-comfy-bridge/python')

from comfy_bridge import ComfyAPI, ComfyWorkflowParser

# Load workflow
parser = ComfyWorkflowParser('/path/to/my_workflow.json')

# Show available inputs
inputs = parser.get_input_nodes()
print(f"Found {len(inputs)} input nodes:")
for node_id, info in inputs.items():
    print(f"  - {info['name']} ({info['class_type']})")

# Execute workflow
api = ComfyAPI()
workflow = parser.get_workflow_copy()
results = api.execute_workflow(workflow)

print(f"Received {len(results)} output images")
```

4. Click "Run Over All Frames" or press Enter

### Method 2: HDA (Full Interface)

Coming soon - currently building HDA with dynamic parameters!

## 6. Verify Output

If successful, you should see:
```
Found 3 input nodes:
  - positive_prompt (CLIPTextEncode)
  - negative_prompt (CLIPTextEncode)
  - dimensions (EmptyLatentImage)
Received 1 output images
```

## Troubleshooting

### "ComfyUI Connected: False"

- Is ComfyUI running? Check http://127.0.0.1:8188
- Try: `curl http://127.0.0.1:8188/system_stats`
- Check firewall settings

### "ModuleNotFoundError: No module named 'comfy_bridge'"

- Check `PYTHONPATH` in Houdini:
  ```python
  import sys
  print('\n'.join(sys.path))
  ```
- Verify path includes `/path/to/houdini-comfy-bridge/python`

### "FileNotFoundError: workflow file not found"

- Use absolute path to workflow JSON
- Check file exists: `os.path.exists('/path/to/workflow.json')`

### No INPUT nodes found

- Verify nodes have `INPUT_` prefix in ComfyUI
- Save workflow in "API Format" (not regular save)
- Check JSON structure in text editor

## Next Steps

✅ **You're all set!** Now try:

1. **Modify parameters**: Edit workflow values and re-execute
2. **Create custom workflows**: Add more INPUT nodes
3. **Batch process**: Loop through seeds/prompts
4. **Read full docs**: See [README.md](README.md) for advanced usage

## Common Workflows

### Text-to-Image

```python
parser = ComfyWorkflowParser('txt2img.json')
updated = parser.update_workflow_inputs({
    'positive_prompt': 'beautiful landscape, sunset, 4k',
    'negative_prompt': 'blurry, ugly',
    'dimensions': [768, 512]
})
api = ComfyAPI()
results = api.execute_workflow(updated)
```

### Multiple Generations

```python
for i in range(10):
    updated = parser.update_workflow_inputs({'seed': i})
    results = api.execute_workflow(updated)
    print(f"Generated image {i+1}")
```

### Image-to-Image

Coming soon!

## Support

- **Issues**: https://github.com/yourusername/houdini-comfy-bridge/issues
- **Docs**: [README.md](README.md)
- **Examples**: [examples/](examples/)

Happy generating! 🎨
