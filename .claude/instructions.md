# Houdini-ComfyUI Bridge - Development Instructions

**Last Updated:** 2025-12-07
**Project Version:** 0.1.0 (Phase 1: Critical Fixes)

## Project Overview

This is a Houdini Digital Asset (HDA) that integrates ComfyUI workflows into Houdini's COP (Compositor) network. It allows users to execute AI image generation workflows from within Houdini, passing images from COPs to ComfyUI and retrieving the results.

**Core Functionality:**
- Load ComfyUI workflow JSON files (API format)
- Detect INPUT_ nodes in workflows to generate Houdini parameters
- Upload input images from Houdini File COPs to ComfyUI
- Execute workflows via ComfyUI REST API
- Retrieve and display output images in Houdini

**Current Status:** Non-functional - HDA needs code update (see context.md)

---

## Architecture & Constraints

### HDA Limitations (CRITICAL)

**1. HDAs CANNOT add dynamic inputs**
- Houdini HDAs have a **fixed** number of inputs defined at creation time
- We CANNOT programmatically add COP inputs based on workflow requirements
- **Solution:** Use a fixed pool of 10 inputs, only connect what's needed

**2. HDAs have limited internal node creation when locked**
- Locked HDAs cannot create internal File nodes for output display
- **Workaround:** Save output to external file path (~/comfyui_output/)
- **Better solution:** Add output_path parameter for user control

**3. HDA PythonModule code is cached**
- Editing external .py files does NOT update HDA automatically
- Must manually copy code into HDA PythonModule via Type Properties dialog
- **Development tip:** Use external script reference with importlib.reload()

### File Structure

```
houdini-comfy-bridge/
├── python/comfy_bridge/          # Core Python library (WORKING)
│   ├── __init__.py
│   ├── comfy_api.py              # ComfyUI REST API client
│   └── comfy_parser.py           # Workflow JSON parser
│
├── scripts/                      # HDA Python modules
│   ├── hda_execute_workflow.py  # Main HDA execution script (LATEST CODE)
│   └── build_hda.py             # HDA builder utility
│
├── otls/                         # Houdini Digital Assets
│   └── comfyui_bridge.hda       # Production HDA (NEEDS UPDATE)
│
├── examples/                     # Example workflows
│   └── example_workflow.json    # Sample API format workflow
│
├── tests/                        # Unit tests
│   ├── test_api.py              # API tests (passing)
│   └── test_parser.py           # Parser tests (passing)
│
└── dev/                          # Development/debug tools
    ├── test_image_upload.py
    └── test_retrieve_image.py
```

### Component Responsibilities

**1. comfy_api.py** - HTTP communication only
- Server health checks
- Image upload/download
- Workflow queue management
- Execution monitoring
- NO workflow parsing or Houdini integration

**2. comfy_parser.py** - Workflow processing only
- JSON loading and format conversion (frontend → API)
- INPUT_ node detection
- Parameter value updates
- NO HTTP requests or Houdini integration

**3. hda_execute_workflow.py** - Houdini integration
- Parameter reading from HDA
- COP image I/O (reading from File COPs)
- Workflow execution orchestration
- Error handling and user feedback

---

## Critical Technical Details

### INPUT_ Node Detection

**How it works:**
1. ComfyUI workflows have nodes with `_meta.title` field
2. If title starts with `INPUT_`, that node becomes a Houdini parameter
3. Example: `_meta.title = "INPUT_positive_prompt"` → HDA parameter `positive_prompt`
4. Parser sanitizes names (lowercase, underscores, no special chars)

**Workflow format requirement:**
- MUST use ComfyUI **API format** (not frontend format)
- API format: `{node_id: {class_type, inputs, _meta}, ...}`
- Frontend format is auto-converted but may have edge cases

### Image Processing Strategy

**Reading from File COPs (WORKING):**
```python
if cop_node.type().name() == 'file':
    file_path = cop_node.parm('filename1').evalAsString()
    file_path = hou.text.expandString(file_path)  # Expand $HIP, $F, etc.
    pil_image = Image.open(file_path)  # Use PIL/Pillow
    # Convert to PNG bytes...
```

**Why this approach:**
- Houdini 21 removed `icopoutput` hscript command
- COP nodes have NO direct pixel access methods
- `cop_node.saveImage()` does NOT exist
- Direct file I/O is fastest and most reliable

**Reading from non-File COPs:**
- NOT CURRENTLY SUPPORTED
- Would require `mwrite` hscript (needs X11 display)
- User must use File COP as input

**Writing output images:**
- HDA is locked → cannot create internal File nodes
- Current solution: Save to `~/comfyui_output/`
- Recommended: Add `output_path` parameter for user control

### Houdini API Gotchas

**Parameter evaluation:**
```python
# String parameters - use evalAsString()
workflow_path = node.parm('workflow_path').evalAsString()  # ✅ Correct

# Int/Float parameters - use eval()
port = node.parm('comfy_port').eval()  # ✅ Correct

# NEVER use eval() on strings - it parses as Python!
server_address = node.parm('server_address').eval()  # ❌ WRONG
# "127.0.0.1:8188" would be evaluated as Python expression!
```

**Path expansion:**
```python
# ALWAYS expand Houdini variables
raw_path = node.parm('output_path').evalAsString()
expanded = hou.text.expandString(raw_path)  # $HIP → /path/to/project
```

**Deprecated commands (DO NOT USE):**
- `hou.hscript("icopoutput")` - Removed in Houdini 21
- `cop_node.saveImage()` - Never existed
- `cop_node.xRes()`, `yRes()` - Only on specific node types

---

## Development Workflow

### Making Code Changes

**1. Edit Python modules:**
```bash
cd /home/maxborg/houdini-comfy-bridge/python/comfy_bridge/
# Edit comfy_api.py or comfy_parser.py
# Changes take effect immediately (Python imports)
```

**2. Edit HDA execution script:**
```bash
cd /home/maxborg/houdini-comfy-bridge/scripts/
# Edit hda_execute_workflow.py
```

**3. Update HDA with new code (REQUIRED):**
```
1. Open Houdini
2. Right-click ComfyUI Bridge node → Type Properties
3. Navigate to: Scripts tab → PythonModule section
4. Open scripts/hda_execute_workflow.py in text editor
5. Copy entire file contents
6. Paste into PythonModule section (replace all)
7. Click: Accept button
8. Click: Apply button
9. Right-click node → Save Node Type
```

**This step is CRITICAL** - Without it, old code runs!

### Testing Changes

**Run unit tests:**
```bash
cd /home/maxborg/houdini-comfy-bridge
python tests/run_tests.py
```

**Test API connection:**
```bash
python dev/test_image_upload.py
```

**Test in Houdini:**
1. Start ComfyUI server: `python /path/to/ComfyUI/main.py`
2. Open Houdini scene
3. Create File COP → load test image
4. Create ComfyUI Bridge node
5. Connect File COP to bridge input
6. Set workflow path
7. Click Execute Workflow
8. Check console output for errors

### Deployment Process

**Before committing:**
1. ✅ Unit tests pass
2. ✅ Integration test passes (Houdini end-to-end)
3. ✅ HDA updated with latest code
4. ✅ Documentation updated (if needed)
5. ✅ No hardcoded paths remain

**Creating release:**
1. Tag version in git
2. Export HDA from Houdini
3. Copy to otls/comfyui_bridge.hda
4. Commit with message: "Release v0.X.Y"

---

## Import Path Management

**In HDA scripts (hda_execute_workflow.py):**
```python
# Use relative path from script location
bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
bridge_path = os.path.abspath(bridge_path)
if bridge_path not in sys.path:
    sys.path.insert(0, bridge_path)
```

**In dev/test scripts:**
```python
# Relative to script location
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
```

**In production (via houdini.env):**
```bash
PYTHONPATH = /path/to/houdini-comfy-bridge/python:$PYTHONPATH
HOUDINI_OTLSCAN_PATH = /path/to/houdini-comfy-bridge/otls:$HOUDINI_OTLSCAN_PATH
```

**NEVER hardcode paths like:**
```python
sys.path.insert(0, '/home/maxborg/houdini-comfy-bridge/python')  # ❌ BAD
```

---

## Debugging Tips

### Common Issues

**1. "Module 'comfy_bridge' not found"**
- Check PYTHONPATH in houdini.env
- Verify python/comfy_bridge/ exists
- Check __init__.py is present

**2. "Old code still running despite edits"**
- HDA PythonModule not updated
- Follow "Update HDA with new code" steps above

**3. "AttributeError: 'str' object has no attribute 'get'"**
- Workflow format issue
- Ensure using API format (not frontend format)
- Check _convert_to_api_format() output

**4. "icopoutput failed: Unknown command"**
- Using old/deprecated Houdini command
- Update to direct File COP reading method

### Debug Output Locations

**Workflow debug files:**
- `/tmp/workflow_debug.json` - Last workflow sent to ComfyUI
- `/tmp/comfyui_payload_debug.json` - Full API payload

**Output images:**
- `~/comfyui_output/` - Default output location

**Houdini console:**
- All print() statements appear here
- Error tracebacks visible

---

## Code Style & Standards

### Python Style
- Follow PEP 8
- Use type hints (typing module)
- Docstrings for all public functions
- NO print() for production code (use hou.ui.setStatusMessage)
- Debug prints: prefix with `[DEBUG]`, `[ERROR]`, etc.

### Error Handling
```python
try:
    # Operation
except SpecificError as e:
    error_msg = f"Clear error description: {str(e)}"
    hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
    print(f"ERROR: {error_msg}")
    import traceback
    traceback.print_exc()  # Full traceback to console
```

### Naming Conventions
- Functions: `snake_case()`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Parameters: `snake_case`
- Private methods: `_leading_underscore()`

---

## Security & Best Practices

**Never commit:**
- API keys or credentials
- Absolute file paths
- Test images (unless small examples)
- Temporary debug files

**Always validate:**
- User input (file paths, server addresses)
- Workflow JSON structure
- Server responses
- Image data before processing

**Performance tips:**
- Cache workflow parsing (parser.cached_workflow)
- Reuse API client instances
- Avoid repeated file I/O
- Use PIL for image processing (faster than numpy)

---

## Additional Resources

**Key Documentation:**
- `ARCHITECTURE.md` - Technical decisions and rationale
- `GOTCHAS.md` - Common pitfalls and lessons learned
- `HOUDINI_API_REFERENCE.md` - Tested Houdini API methods
- `ACTION_PLAN.md` - Current task roadmap
- `.claude/context.md` - Current project state

**External Resources:**
- ComfyUI API: https://github.com/comfyanonymous/ComfyUI
- Houdini Python API: https://www.sidefx.com/docs/houdini/hom/
- PIL/Pillow: https://pillow.readthedocs.io/

---

**Remember:** When in doubt, check context.md for current state and NEXT_STEPS.md for priorities!
