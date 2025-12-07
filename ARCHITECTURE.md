# Architecture & Technical Decisions

**Last Updated:** 2025-12-07
**Project:** Houdini-ComfyUI Bridge v0.1.0

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Design Decisions](#design-decisions)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Technical Constraints](#technical-constraints)
6. [Trade-offs & Alternatives](#trade-offs--alternatives)

---

## System Overview

### Purpose

The Houdini-ComfyUI Bridge enables AI image generation workflows from within Houdini's COP (Compositor) network, allowing artists to leverage ComfyUI's node-based diffusion workflows without leaving Houdini.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Houdini COP Network                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐      ┌──────────────────────┐      ┌──────────┐ │
│  │ File COP │─────▶│  ComfyUI Bridge HDA  │─────▶│ File COP │ │
│  │ (Input)  │      │                      │      │ (Output) │ │
│  └──────────┘      └──────────────────────┘      └──────────┘ │
│                              │                                  │
│                              │ REST API (HTTP)                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   ComfyUI Server    │
                    │  (localhost:8188)   │
                    ├─────────────────────┤
                    │  - Workflow Queue   │
                    │  - Model Loading    │
                    │  - Image Processing │
                    │  - Result Storage   │
                    └─────────────────────┘
```

### Three-Layer Architecture

**Layer 1: API Communication (comfy_api.py)**
- Pure HTTP client, no domain logic
- Handles REST endpoints, multipart uploads
- Polling-based execution monitoring

**Layer 2: Workflow Processing (comfy_parser.py)**
- JSON parsing and format conversion
- INPUT_ node detection and mapping
- Workflow value updates

**Layer 3: Houdini Integration (hda_execute_workflow.py)**
- HDA parameter management
- COP image I/O
- Orchestration and error handling

---

## Design Decisions

### Decision 1: External Python Modules vs Embedded HDA Code

**Decision:** Use external Python package (comfy_bridge) + thin HDA wrapper

**Rationale:**
- **Testability:** Can unit test core logic outside Houdini
- **Reusability:** Core modules usable in scripts, shelf tools, batch processing
- **Development Speed:** Edit .py files directly, no HDA reload needed
- **Version Control:** Git-friendly Python files vs binary .hda files
- **Maintainability:** Clear separation of concerns

**Trade-offs:**
- ✅ Easier to develop and test
- ✅ Better code organization
- ❌ Requires PYTHONPATH setup (houdini.env)
- ❌ Two places to update (module + HDA)

**Alternatives Considered:**

**Option A: All code embedded in HDA**
```
Pros:
- Single file distribution
- No environment setup needed
- User just loads .hda file

Cons:
- Can't unit test without Houdini
- Hard to version control (binary format)
- Must reload HDA for every change
- No code reuse outside HDA
```
**Rejected:** Development friction too high

**Option B: Pure Python, no HDA**
```
Pros:
- Maximum flexibility
- Easiest to test
- No HDA complexity

Cons:
- No UI integration
- User must write code
- Not artist-friendly
```
**Rejected:** Not a COP node, defeats purpose

**Final Decision:** Hybrid approach (external modules + HDA wrapper) provides best balance.

---

### Decision 2: Fixed Input Pool vs Dynamic Inputs

**Decision:** Fixed pool of 10 inputs (1 used, 9 reserved for future)

**Rationale:**
- **HDA Limitation:** Cannot programmatically add inputs to locked HDAs
- **Houdini Constraint:** Input count defined at HDA creation time
- **Simplicity:** Most workflows need 0-1 input images

**Implementation:**
```python
# In build_hda.py
hda = base_node.createDigitalAsset(
    name='comfy_bridge',
    hda_file_name=hda_path,
    min_num_inputs=0,      # Optional input
    max_num_inputs=1       # Only support 1 for now
)
```

**Trade-offs:**
- ✅ Works within HDA constraints
- ✅ Simple for most use cases
- ❌ Can't handle multi-image workflows (rare)
- ❌ Reserved inputs waste slots

**Future Enhancement:**
- Expand to max_num_inputs=10 when needed
- Document which input maps to which workflow node

---

### Decision 3: PIL/Pillow for Image Processing

**Decision:** Use PIL (Pillow) for all image operations

**Rationale:**
- **Standard Library:** Often included with Houdini Python
- **Format Support:** PNG, JPEG, TIFF, etc.
- **Memory Efficient:** BytesIO for in-memory operations
- **Simple API:** Easy to use and understand

**Alternatives Considered:**

**Option A: Houdini COP API**
```python
# Attempted:
cop_node.saveImage(path)      # ❌ Doesn't exist
cop_node.allPixels()          # ❌ Doesn't work on File nodes
hou.hscript("icopoutput")     # ❌ Removed in Houdini 21
```
**Rejected:** API doesn't support our use case

**Option B: NumPy + OpenCV**
```python
# Import numpy, opencv-python
# Convert COP → numpy array → bytes
```
**Pros:** More image processing options
**Cons:** External dependencies, larger install, slower
**Rejected:** Overhead not justified for simple I/O

**Final Decision:** PIL provides exactly what we need with minimal dependencies.

---

### Decision 4: Direct File I/O Instead of COP Pixel Access

**Decision:** Read File COP source files directly, bypass COP rendering

**Rationale:**
- **API Limitations:** Houdini COP2 has no direct pixel access
- **Deprecated Commands:** icopoutput removed in Houdini 21
- **Performance:** Direct file reading faster than rendering
- **Reliability:** File I/O well-tested and stable

**Implementation:**
```python
if cop_node.type().name() == 'file':
    file_path = cop_node.parm('filename1').evalAsString()
    file_path = hou.text.expandString(file_path)  # Expand $HIP, etc.
    pil_image = Image.open(file_path)
    # Convert to PNG bytes...
```

**Why This Works:**
1. File COP just loads an image file
2. We read the same source file
3. Bypass COP rendering entirely
4. Get raw pixel data via PIL

**Limitations:**
- Only works for File COP nodes
- Doesn't work for rendered/composite COPs
- User must save composite to file first

**Future Enhancement:**
- Support non-File COPs via mwrite command
- Requires X11 display (headless won't work)
- More complex, lower priority

---

### Decision 5: INPUT_ Convention for Workflow Detection

**Decision:** Use `INPUT_` prefix in ComfyUI node titles to mark controllable parameters

**Rationale:**
- **Simple:** Easy for users to understand
- **Non-invasive:** Doesn't change workflow structure
- **Flexible:** Works with any node type
- **Standard:** Follows naming convention patterns

**How It Works:**
```json
{
  "1": {
    "inputs": {"text": "a beautiful landscape"},
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "INPUT_positive_prompt"  ← Marks as input
    }
  }
}
```

**Parser extracts:**
- Node ID: `"1"`
- Parameter name: `"positive_prompt"` (strips INPUT_ prefix)
- Class type: `"CLIPTextEncode"` (determines Houdini param type)
- Default value: `"a beautiful landscape"`

**Alternatives Considered:**

**Option A: Dedicated input node type**
- Requires custom ComfyUI node
- Not compatible with existing workflows
**Rejected:** Too invasive

**Option B: JSON sidecar file**
- Separate file defines inputs
- Must keep in sync with workflow
**Rejected:** Too complex, error-prone

**Option C: Node IDs in config file**
- List node IDs in bridge config
- No workflow changes needed
**Rejected:** Less discoverable, harder to maintain

**Final Decision:** INPUT_ prefix is simplest and most intuitive.

---

### Decision 6: Workflow Format Conversion (Frontend → API)

**Decision:** Auto-convert ComfyUI frontend format to API format

**Rationale:**
- **User Experience:** Users export workflows in frontend format by default
- **Compatibility:** Support both formats transparently
- **Robustness:** Handle variations in workflow exports

**Format Differences:**

**Frontend Format (from "Save" button):**
```json
{
  "nodes": [
    {
      "id": 1,
      "type": "CLIPTextEncode",
      "widgets_values": ["hello world"]
    }
  ],
  "links": [[0, 1, 0, 2, 1, "IMAGE"]],
  "version": 0.4
}
```

**API Format (from "Save (API Format)" button):**
```json
{
  "1": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "hello world"
    }
  }
}
```

**Conversion Logic (comfy_parser.py:77-183):**
1. Detect format (has `nodes` key → frontend format)
2. Build link map from links array
3. Convert each node:
   - id → string key
   - type → class_type
   - widgets_values → inputs dict (type-aware matching)
   - title → _meta.title
4. Replace connections with `[node_id, slot]` references

**Trade-offs:**
- ✅ Users can export either format
- ✅ Don't need to document format requirement
- ❌ More code complexity
- ❌ Edge cases in type matching

**Future Enhancement:**
- Stricter type matching
- Validation errors with helpful messages
- Support for more complex widget types

---

## Component Architecture

### comfy_api.py - HTTP Client

**Responsibilities:**
- HTTP request/response handling
- Multipart form encoding (image uploads)
- JSON payload construction
- Polling for completion
- Error handling and retries

**Key Methods:**
```python
is_server_alive() → bool
upload_image(bytes, filename) → dict
queue_prompt(workflow) → dict
wait_for_completion(prompt_id, timeout) → dict
get_image(filename, folder_type) → bytes
execute_workflow(workflow, timeout) → List[Tuple[str, bytes]]
```

**Design Principles:**
- Stateless (except client_id)
- No Houdini dependencies
- Pure Python stdlib (urllib, json)
- Synchronous (polling-based)

**Why Synchronous?**
- Simpler code, easier to debug
- Houdini UI blocks anyway during execution
- Async not needed for single-workflow execution
- Future: Could add async for batch processing

---

### comfy_parser.py - Workflow Processing

**Responsibilities:**
- JSON file loading
- Format detection and conversion
- INPUT_ node extraction
- Parameter type inference
- Workflow value updates

**Key Methods:**
```python
load_workflow(path) → dict
_convert_to_api_format(workflow) → dict
_extract_input_nodes() → None (populates self.input_nodes)
get_input_parameters() → List[dict]
update_workflow_inputs(values) → dict
```

**Design Principles:**
- Pure data transformation
- No I/O except file loading
- No Houdini dependencies
- Extensive type checking

**Type Inference Logic:**
```python
class_type → Houdini param type
LoadImage → file (string, file picker)
CLIPTextEncode → string (text input)
EmptyLatentImage → intvector2 (width/height)
KSampler → folder (group of params)
Generic → infer from inputs
```

---

### hda_execute_workflow.py - Houdini Integration

**Responsibilities:**
- Read HDA parameters
- Validate user input
- Read File COP source images
- Orchestrate API calls
- Write output images
- Error handling and user feedback

**Key Functions:**
```python
execute_workflow(node) → None
_read_cop_image_as_png(cop_node) → bytes
_write_png_to_cop(node, png_data, plane_name) → None
```

**Design Principles:**
- Main entry point for HDA
- Handles all Houdini-specific code
- User-facing error messages
- Debug logging to console

**Error Handling Strategy:**
```python
try:
    # Operation
except FileNotFoundError as e:
    # Specific error type
    hou.ui.displayMessage(f"File not found: {e}", severity=Error)
except ConnectionError as e:
    # Network errors
    hou.ui.displayMessage(f"Connection error: {e}", severity=Error)
except Exception as e:
    # Catch-all with traceback
    hou.ui.displayMessage(f"Execution failed: {e}", severity=Error)
    traceback.print_exc()  # Full trace to console
```

---

## Data Flow

### End-to-End Execution Flow

```
1. User clicks "Execute Workflow" button in HDA
   ↓
2. execute_workflow(node) called
   ↓
3. Read HDA parameters (workflow_path, server_address)
   ↓
4. Initialize ComfyAPI and ComfyWorkflowParser
   ↓
5. Check server alive (is_server_alive())
   ↓
6. Load workflow JSON (parser.load_workflow())
   ↓
7. Extract INPUT_ nodes (parser._extract_input_nodes())
   ↓
8. If input COP connected:
   ├─ Read File COP source (_read_cop_image_as_png())
   ├─ Convert to PNG bytes (PIL)
   └─ Upload to ComfyUI (api.upload_image())
   ↓
9. Collect parameter values from HDA
   ↓
10. Update workflow with values (parser.update_workflow_inputs())
    ↓
11. Execute workflow (api.execute_workflow())
    ├─ Queue prompt (api.queue_prompt())
    ├─ Wait for completion (api.wait_for_completion())
    └─ Download images (api.get_image())
    ↓
12. Write output images (_write_png_to_cop())
    ├─ Try to create internal File node
    └─ Fallback: save to ~/comfyui_output/
    ↓
13. Show success message (hou.ui.setStatusMessage())
```

### Image Data Transformation Pipeline

```
File on disk (source.png)
    ↓ PIL.Image.open()
PIL Image object (RGB/RGBA)
    ↓ image.convert('RGB')
PIL Image object (RGB)
    ↓ image.save(BytesIO, format='PNG')
PNG bytes in memory
    ↓ api.upload_image()
HTTP multipart/form-data
    ↓ ComfyUI server
Saved to ComfyUI/input/houdini_input.png
    ↓ Workflow execution
Processed image (diffusion model)
    ↓ ComfyUI SaveImage node
Saved to ComfyUI/output/filename.png
    ↓ api.get_image()
PNG bytes in memory
    ↓ _write_png_to_cop()
Saved to ~/comfyui_output/filename.png
    ↓ User action
Loaded in Houdini File COP
```

---

## Technical Constraints

### Houdini Limitations

**1. No Dynamic Input Creation**
- HDAs have fixed input count
- Cannot programmatically add COP inputs
- Workaround: Fixed pool of 10 inputs

**2. Limited COP Pixel Access**
- No cop_node.saveImage() method
- No direct pixel array access for File nodes
- icopoutput command removed (Houdini 21)
- Workaround: Direct file I/O

**3. Locked HDA Restrictions**
- Can't create internal nodes when locked
- Can't modify network structure
- Workaround: Save output to external path

**4. HDA Code Caching**
- PythonModule cached in memory
- Editing external files doesn't update HDA
- Workaround: Manual copy/paste into Type Properties

### ComfyUI Limitations

**1. Synchronous-Only API**
- No WebSocket for real-time updates
- Must poll /history endpoint
- No progress callbacks
- Workaround: Polling with timeout

**2. No Batch Upload**
- One image per upload request
- Can't upload multiple inputs simultaneously
- Workaround: Loop uploads (future)

**3. Workflow Format Fragmentation**
- Two export formats (frontend vs API)
- Different node structures
- Workaround: Auto-conversion in parser

---

## Trade-offs & Alternatives

### Current Trade-offs

**✅ Chose Simplicity:**
- Synchronous API (vs async)
- Polling (vs WebSocket)
- File I/O (vs pixel access)
- External modules (vs embedded)

**Result:** Easy to understand, maintain, and debug

**❌ Sacrificed:**
- Real-time progress updates
- Support for non-File COPs
- Single-file distribution
- Dynamic input count

**Result:** Some limitations, but core use case works well

### Future Improvements

**When to reconsider decisions:**

**1. Add WebSocket support** → When users need real-time progress
- More complex code
- Better UX during long renders

**2. Support non-File COPs** → When users need composite inputs
- Implement mwrite workaround
- Requires X11 display (no headless)

**3. Dynamic inputs** → When multi-image workflows common
- Would require unlocked HDA
- Less polished UX

**4. Async API** → When adding batch processing
- More complex error handling
- Better performance for multiple workflows

---

## Summary

The Houdini-ComfyUI Bridge uses a **three-layer architecture** with clear separation between HTTP communication, workflow processing, and Houdini integration. Key decisions prioritize **simplicity, testability, and reliability** over advanced features.

**Core principles:**
- External Python modules for testability
- Direct file I/O to work around API limitations
- Polling-based synchronous execution
- INPUT_ convention for workflow parameterization

These decisions provide a solid foundation while remaining flexible for future enhancements.
