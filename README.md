# Houdini-ComfyUI Bridge

A Houdini COP node that dynamically integrates ComfyUI workflows, allowing seamless AI image generation within Houdini's compositing context.

## Features

- **Dynamic Parameter Generation**: Automatically creates Houdini parameters from ComfyUI workflow JSON files
- **INPUT Convention**: Uses `INPUT_` prefix in node titles to identify controllable parameters
- **REST API Communication**: Direct communication with ComfyUI server (localhost:8188)
- **Multiple Output Support**: Handles multiple output images from workflows
- **COP Integration**: Native Houdini Compositor (COP) node for image processing
- **Workflow Caching**: Efficient workflow loading with caching fallback
- **Real-time Execution**: Execute workflows directly from Houdini with progress feedback

## Architecture

### 1. Python API Layer (`comfy_api.py`)
Handles all HTTP communication with ComfyUI server:
- Image upload/download
- Workflow queue management
- Execution monitoring
- Server health checks

### 2. Workflow Parser (`comfy_parser.py`)
Processes ComfyUI workflow JSON files:
- Extracts nodes with `INPUT_` prefix
- Generates Houdini parameter templates
- Updates workflow with user values
- Type inference and parameter mapping

### 3. COP Node (`comfy_cop_node.py`)
Main Houdini integration:
- Dynamic UI generation
- Workflow file loading
- Parameter collection and mapping
- Execution callbacks

## Installation

### Prerequisites
- Houdini 19.5+ (Python 3.9+)
- ComfyUI running locally or on network
- Python standard library (no external dependencies)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/houdini-comfy-bridge.git
   cd houdini-comfy-bridge
   ```

2. **Add to Houdini environment**:

   Edit your `houdini.env` file (typically in `~/houdini19.5/`):
   ```bash
   # Add Python path
   PYTHONPATH = /path/to/houdini-comfy-bridge/python:$PYTHONPATH

   # Add HDA path
   HOUDINI_OTLSCAN_PATH = /path/to/houdini-comfy-bridge/otls:$HOUDINI_OTLSCAN_PATH

   # Add scripts path
   HOUDINI_SCRIPT_PATH = /path/to/houdini-comfy-bridge/scripts:$HOUDINI_SCRIPT_PATH
   ```

3. **Build the HDA** (optional - if creating from scratch):

   In Houdini Python Shell:
   ```python
   import sys
   sys.path.append('/path/to/houdini-comfy-bridge/scripts')
   import build_hda
   build_hda.create_comfy_cop_hda()
   ```

4. **Start ComfyUI**:
   ```bash
   cd /path/to/ComfyUI
   python main.py
   ```
   ComfyUI should be running at `http://127.0.0.1:8188`

## Usage

### Creating INPUT Nodes in ComfyUI

To make parameters controllable from Houdini, rename nodes in ComfyUI with the `INPUT_` prefix:

1. In ComfyUI, right-click a node → Properties
2. Set the title to `INPUT_<parameter_name>`
3. Save the workflow as JSON (via "Save (API Format)" button)

**Example**:
- `INPUT_positive_prompt` → Creates "Positive Prompt" parameter in Houdini
- `INPUT_negative_prompt` → Creates "Negative Prompt" parameter
- `INPUT_dimensions` → Creates width/height vector parameter
- `INPUT_sampler_settings` → Creates sampler configuration folder

### In Houdini

1. **Create COP Network**:
   - In Network View, create a COP network (`/img`)

2. **Add ComfyUI Bridge Node**:
   - Inside the COP network, press Tab → type "comfy" → select "ComfyUI Bridge"

3. **Configure Server**:
   - Set "ComfyUI Host" (default: `127.0.0.1`)
   - Set "ComfyUI Port" (default: `8188`)
   - Click "Test Connection" to verify

4. **Load Workflow**:
   - Click the folder icon next to "Workflow File"
   - Select your ComfyUI workflow JSON file
   - Parameters will automatically generate in the "Workflow Inputs" folder

5. **Adjust Parameters**:
   - Modify generated parameters as needed
   - Each `INPUT_` node becomes an editable parameter

6. **Execute**:
   - Click "Execute Workflow" button
   - Monitor progress in Houdini's status bar
   - Output images appear in the COP node

### Example Workflow

See `examples/example_workflow.json` for a complete example with:
- Text prompt inputs (positive/negative)
- Dimension controls (width/height)
- Sampler settings (seed, steps, CFG)
- Checkpoint loading
- Image generation and output

## Workflow Format

### Standard ComfyUI Node
```json
{
  "1": {
    "inputs": {
      "text": "a beautiful landscape"
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode"
    }
  }
}
```

### INPUT Node (Controllable from Houdini)
```json
{
  "1": {
    "inputs": {
      "text": "a beautiful landscape"
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "INPUT_prompt"
    }
  }
}
```

The `INPUT_` prefix in `_meta.title` marks this node for Houdini control.

## Parameter Type Mapping

| ComfyUI Class | Houdini Parameter | Description |
|---------------|-------------------|-------------|
| `LoadImage` | File path | Image file picker |
| `CLIPTextEncode` | String | Text input field |
| `EmptyLatentImage` | Int Vector2 | Width/height dimensions |
| `KSampler` | Folder | Sampler settings group |
| `SaveImage` | Toggle | Output control |
| Generic | Auto-detected | Based on input types |

## API Reference

### ComfyAPI

```python
from comfy_bridge import ComfyAPI

api = ComfyAPI(host='127.0.0.1', port=8188)

# Check server
if api.is_server_alive():
    print("Connected!")

# Execute workflow
workflow = {...}  # Your workflow dict
results = api.execute_workflow(workflow)

# Results is list of (filename, image_bytes) tuples
for filename, image_data in results:
    print(f"Received: {filename}")
```

### ComfyWorkflowParser

```python
from comfy_bridge import ComfyWorkflowParser

parser = ComfyWorkflowParser('workflow.json')

# Get input nodes
inputs = parser.get_input_nodes()

# Get parameter definitions
params = parser.get_input_parameters()

# Update workflow with new values
updated = parser.update_workflow_inputs({
    'prompt': 'new prompt text',
    'dimensions': [1024, 1024]
})
```

## Directory Structure

```
houdini-comfy-bridge/
├── python/
│   └── comfy_bridge/
│       ├── __init__.py
│       ├── comfy_api.py          # API communication layer
│       └── comfy_parser.py       # Workflow parser
├── scripts/
│   ├── comfy_cop_node.py         # Main COP node implementation
│   └── build_hda.py              # HDA builder script
├── otls/
│   └── comfy_bridge.hda          # Compiled HDA (generated)
├── hda/
│   └── (HDA development files)
├── examples/
│   └── example_workflow.json     # Example workflow
├── tests/
│   ├── test_api.py
│   └── test_parser.py
└── README.md
```

## Testing

### Test API Connection

```python
from comfy_bridge import ComfyAPI

api = ComfyAPI()
print(f"Server alive: {api.is_server_alive()}")
print(f"Queue info: {api.get_queue_info()}")
```

### Test Workflow Parsing

```python
from comfy_bridge import ComfyWorkflowParser

parser = ComfyWorkflowParser('examples/example_workflow.json')
print(f"Input nodes: {parser.get_input_nodes()}")
print(f"Parameters: {parser.get_input_parameters()}")
```

## Troubleshooting

### "Failed to connect to ComfyUI"
- Ensure ComfyUI is running: `http://127.0.0.1:8188`
- Check firewall settings
- Verify host/port in node parameters

### "No workflow loaded"
- Ensure workflow file path is correct
- Check JSON syntax in workflow file
- Click "Reload Workflow" button

### "Workflow execution failed"
- Check ComfyUI console for errors
- Verify all model files are available
- Ensure INPUT node names match parameter names

### Parameters not generating
- Verify nodes have `INPUT_` prefix in `_meta.title`
- Reload workflow after changes
- Check Houdini Python Shell for errors

## Advanced Usage

### Custom Parameter Types

You can extend parameter type detection by modifying `comfy_parser.py`:

```python
# In _generate_parameter_definition method
type_mappings = {
    'YourCustomNode': {'type': 'custom', 'parm_type': 'string'},
    # Add more mappings...
}
```

### Input Images from COPs

To send Houdini COP images to ComfyUI:

1. Connect input COP to ComfyUI Bridge node
2. Node will extract image data
3. Upload to ComfyUI automatically
4. Update workflow's LoadImage nodes

### Batch Processing

For multiple workflow executions:

```python
import hou

node = hou.node('/img/cop2net1/comfy_bridge1')
handler = comfy_cop_node.ComfyCOPNode(node)

for seed in range(10):
    input_values = {'sampler_settings': {'seed': seed}}
    workflow = handler.parser.update_workflow_inputs(input_values)
    results = handler.api.execute_workflow(workflow)
    # Process results...
```

## Roadmap

- [ ] Input image support (COP → ComfyUI)
- [ ] Batch processing interface
- [ ] Workflow template library
- [ ] Progress bar during execution
- [ ] Output image sequence support
- [ ] WebSocket support for real-time updates
- [ ] SOP node for geometry-based workflows
- [ ] Parameter presets and sharing

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Credits

- Built for Houdini by the community
- ComfyUI: https://github.com/comfyanonymous/ComfyUI
- Integrates with SideFX Houdini: https://www.sidefx.com/

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/yourusername/houdini-comfy-bridge/issues
- SideFX Forums: https://www.sidefx.com/forum/
- ComfyUI Discord: https://discord.gg/comfyui
