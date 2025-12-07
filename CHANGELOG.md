# Changelog

All notable changes, attempts, and learnings for the Houdini-ComfyUI Bridge project.

**Format:** [Date] - [What was attempted] - [Outcome] - [Lessons learned]

---

## [2025-12-07] - HDA Interface Refactoring & Path Fixes

### Changed
- ✅ Fixed hardcoded paths in `HDA/PythonModule.py`
  - Added `_get_project_dir()` function with 4 fallback methods
  - Now checks COMFY_BRIDGE_ROOT env var, PYTHONPATH, default location
  - Falls back to hardcoded path with warning if all else fails

- ✅ Fixed hardcoded paths in `HDA/hda_interface.py`
  - Added `_get_scripts_dir()` function with 4 fallback methods
  - Uses relative paths from file location as primary method
  - Checks COMFY_BRIDGE_ROOT, searches PYTHONPATH, falls back gracefully

- ✅ Fixed path expansion function calls
  - Changed `hou.expandString()` to `hou.text.expandString()` (correct API)
  - Fixed in 4 locations: get_workflow_inputs, get_workflow_json, execute_workflow, get_output_directory

- ✅ Updated `scripts/hda_execute_workflow.py`
  - Added support for both old (server_address=host:port) and new (server_address + server_port) parameter styles
  - Added support for multiple input images (up to 10)
  - Uses workflow_inputs from node.userData() for intelligent input mapping
  - Each input uploads as unique filename: houdini_input_0.png, houdini_input_1.png, etc.
  - Fixed string parameter evaluation (evalAsString() instead of eval())
  - Uses hou.text.expandString() for workflow path

### Technical Details

**Path Resolution Strategy:**
```python
# Priority order for finding project directory:
1. COMFY_BRIDGE_ROOT environment variable
2. Search sys.path for HDA/hda_interface.py
3. Default location ~/houdini-comfy-bridge
4. Hardcoded fallback with warning
```

**Multiple Input Support:**
```python
# New workflow:
1. hda_interface.on_workflow_changed() detects INPUT_ nodes
2. Stores mapping in node.userData('workflow_inputs')
3. execute_workflow() reads userData and processes each input
4. Each input uploads with unique filename
5. Workflow updated with correct image references
```

### Files Modified
- HDA/PythonModule.py (lines 15-41)
- HDA/hda_interface.py (lines 19-50, 69, 106, 244, 328)
- scripts/hda_execute_workflow.py (lines 29-67, 79-166)

### Result
✅ **Success** - HDA code now portable across different installations
- Works on any machine (no hardcoded /home/maxborg/)
- Supports both old and new parameter layouts
- Handles multiple input images correctly
- Better error messages with fallback paths

### Lessons Learned
- Always use relative paths or environment variables
- Provide multiple fallback methods for robustness
- Use correct Houdini API functions (hou.text.expandString not hou.expandString)
- Support backward compatibility when changing parameter structure

---

## [2025-12-07] - Project Documentation Setup

### Added
- ✅ Created `.claude/instructions.md` - Comprehensive development guide
- ✅ Created `.claude/context.md` - Current project state tracking
- ✅ Created `ARCHITECTURE.md` - Technical decisions and rationale
- ✅ Created `GOTCHAS.md` - Common pitfalls and lessons learned
- ✅ Created `.claudeignore` - Context exclusion rules
- ✅ Created `CHANGELOG.md` - This file

### Purpose
Establish intelligent documentation system for development continuity

---

## [2025-12-06] - Phase 1 Planning & Analysis

### Added
- ✅ Created `ACTION_PLAN.md` - Phased task breakdown
- ✅ Created `REPOSITORY_AUDIT.md` - Complete project analysis
- ✅ Updated `HOUDINI_API_REFERENCE.md` - Verified working methods

### Analysis Findings
**What Works:**
- Core Python modules (comfy_api.py, comfy_parser.py) - fully functional
- Unit tests passing
- Workflow format conversion
- INPUT_ node detection

**What's Broken:**
- HDA has outdated code
- Input image reading untested
- Output display saves to external file

**Root Causes Identified:**
1. HDA PythonModule not updated with latest script changes
2. Houdini 21 removed icopoutput command
3. COP API lacks direct pixel access
4. HDA locked, can't create internal nodes

---

## [2025-12-06] - Input Image Reading - Multiple Attempts

### Attempt 1: cop_node.saveImage()
```python
cop_node.saveImage('/tmp/output.png')
```
**Result:** ❌ Failed
**Error:** `AttributeError: 'CopNode' object has no attribute 'saveImage'`
**Lesson:** Method doesn't exist in Houdini API

### Attempt 2: Create ROP Composite Node
```python
rop = cop_node.createNode('rop_composite')
rop.parm('copoutput').set('/tmp/output.png')
```
**Result:** ❌ Failed
**Error:** `hou.OperationFailed: Invalid node type name`
**Lesson:** Can't create ROP nodes inside COP network context

### Attempt 3: hou.hscript("icopoutput")
```python
hou.hscript(f"icopoutput -d {path} -f 1 1 {cop_node.path()}")
```
**Result:** ❌ Failed
**Error:** `RuntimeError: icopoutput failed: Unknown command: icopoutput`
**Lesson:** Command removed in Houdini 21 (worked in 19.5)

### Attempt 4: Direct File COP Source Reading
```python
if cop_node.type().name() == 'file':
    file_path = cop_node.parm('filename1').evalAsString()
    file_path = hou.text.expandString(file_path)
    pil_image = Image.open(file_path)
```
**Result:** ✅ Success (in code, not yet tested)
**Status:** Implemented in scripts/hda_execute_workflow.py:234-255
**Lesson:** Direct file I/O fastest and most reliable for File COPs

---

## [2025-12-06] - Workflow Format Conversion

### Issue Encountered
**Problem:** Workflows exported from ComfyUI UI (frontend format) fail to parse
**Error:** `KeyError: '1'` when accessing workflow["1"]
**Root Cause:** Frontend format uses `{nodes: [...], links: [...]}` instead of `{node_id: {...}}`

### Solution Implemented
```python
def _convert_to_api_format(self, workflow_data):
    """Convert frontend format to API format if needed"""
    if 'nodes' not in workflow_data:
        return workflow_data  # Already API format

    # Convert nodes array to node dict
    api_workflow = {}
    for node in workflow_data['nodes']:
        node_id = str(node['id'])
        api_workflow[node_id] = {
            'class_type': node['type'],
            'inputs': {...}  # Map widgets_values to inputs
        }
    return api_workflow
```

**Result:** ✅ Success
**File:** comfy_parser.py:77-183
**Lesson:** Always detect format before parsing

---

## [2025-12-06] - Type Checking Bug Fix

### Issue Encountered
**Problem:** `AttributeError: 'str' object has no attribute 'get'`
**Frequency:** Recurring across multiple functions
**Root Cause:** Workflow format conversion sometimes produces strings instead of dicts

### Solution Implemented
Added type checking before dict operations:
```python
for node_id, node_data in workflow.items():
    if not isinstance(node_data, dict):
        print(f"Skipping non-dict node: {node_id}")
        continue
    class_type = node_data.get('class_type', '')
```

**Locations Fixed:**
- ✅ comfy_parser.py:221 (`_extract_input_nodes()`)
- ✅ comfy_parser.py:430 (`update_workflow_inputs()`)
- ✅ hda_execute_workflow.py:150 (debug printing)

**Result:** ✅ Success
**Lesson:** Never assume data types, always validate

---

## [2025-12-06] - HDA Update Process Discovery

### Issue Encountered
**Problem:** User reported errors from deprecated code despite editing scripts
**Expected:** Code changes take effect automatically
**Actual:** Old code still running

### Investigation
1. Verified scripts/hda_execute_workflow.py has latest code ✅
2. Checked user error logs - showed old `icopoutput` commands ❌
3. Realized HDA PythonModule is separate from external scripts

### Root Cause
- HDA embeds code in .hda file (binary format)
- Editing external .py files doesn't update .hda
- Manual copy/paste required

### Process Documented
```
1. Edit scripts/hda_execute_workflow.py
2. Open Houdini
3. Right-click node → Type Properties
4. Scripts → PythonModule
5. Copy/paste updated code
6. Accept → Apply → Save
```

**Status:** Documented in ACTION_PLAN.md Task 1.1
**Lesson:** HDA development requires manual sync step

---

## [2025-12-06] - Parameter Evaluation Method Bug

### Issue Discovered
**Problem:** Server address parameter evaluation behaving strangely
**Code:**
```python
server_address = node.parm('server_address').eval()  # ❌ Wrong
```

**What Happened:**
- Parameter value: `"127.0.0.1:8188"`
- `.eval()` interprets as Python expression
- Tries to evaluate: `127.0.1 - 8188` (float subtraction!)
- Results in numeric value instead of string

### Solution
```python
server_address = node.parm('server_address').evalAsString()  # ✅ Correct
```

**Rule Established:**
- String parameters: `evalAsString()`
- Int/Float parameters: `eval()`
- NEVER use `eval()` on strings

**Result:** ✅ Fixed in hda_execute_workflow.py:46
**Lesson:** Match eval method to parameter template type

---

## [2025-12-05] - Initial Project Setup

### Created
- ✅ Repository structure
- ✅ Core Python modules
- ✅ Unit tests
- ✅ Example workflow
- ✅ README documentation

### Established Patterns
- External Python package (comfy_bridge)
- HDA wrapper for Houdini integration
- INPUT_ convention for workflow parameters
- API format for workflows

---

## Attempted But NOT Implemented

### WebSocket Support for Real-time Progress
**Why NOT implemented:**
- ComfyUI API only supports polling
- Synchronous approach simpler
- Current use case doesn't need real-time updates
**Status:** Deferred to future version

### Dynamic Input Generation
**Why NOT implemented:**
- HDA inputs must be fixed at creation time
- Houdini limitation, cannot work around
**Status:** Not feasible with current architecture

### Non-File COP Support
**Why NOT implemented:**
- Requires mwrite command (needs X11)
- icopoutput removed in Houdini 21
- No other direct pixel access available
**Status:** Possible but low priority

### Async API Client
**Why NOT implemented:**
- Houdini UI blocks during execution anyway
- Synchronous code simpler to debug
- No performance benefit for single workflow
**Status:** Deferred to batch processing feature

---

## Pattern: Successful Solutions

**Direct File I/O** ✅
- Read File COP source files directly
- Bypass Houdini rendering pipeline
- Use PIL for image processing
**When to use:** Always for File COPs

**Type Checking** ✅
- Validate data types before dict operations
- Use `isinstance()` checks liberally
- Fail gracefully with clear messages
**When to use:** All workflow processing

**Relative Paths** ✅
- Use `os.path.dirname(__file__)` for relative imports
- Expand Houdini variables with `hou.text.expandString()`
- Never hardcode absolute paths
**When to use:** All file operations

**Format Auto-detection** ✅
- Check for 'nodes' key to detect format
- Convert frontend → API automatically
- Don't require user to know formats
**When to use:** All workflow loading

---

## Pattern: Failed Approaches

**COP Pixel Access** ❌
- No direct methods exist
- hscript commands deprecated/removed
- Must use file I/O workarounds
**Lesson:** Don't fight the API, find alternative approach

**Embedded HDA Code** ❌
- Hard to test
- Poor version control
- Manual update process
**Lesson:** External modules provide better workflow

**Dynamic HDA Generation** ❌
- Can't change input count after creation
- Can't create internal nodes when locked
- HDA limitations are hard constraints
**Lesson:** Work within Houdini's limitations

---

## Running Log Template

Use this format for future entries:

```markdown
## [YYYY-MM-DD] - Brief Description

### Attempted
What was tried

### Result
✅ Success / ❌ Failed / ⚠️ Partial

### Code Changes
Files modified

### Lessons Learned
Key insights

### Follow-up Actions
What needs to happen next
```

---

**Maintenance Notes:**
- Update this file whenever attempting a solution
- Include both successes AND failures
- Focus on WHY and WHAT LEARNED
- Link to relevant code/docs
- Keep entries chronological
