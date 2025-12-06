# Houdini-ComfyUI Bridge - Repository Audit & Analysis

**Date:** 2025-12-06
**Audited By:** Claude Code
**Status:** Pre-Production / Development

---

## 1. PROJECT AUDIT

### 1.1 Complete File Inventory

#### ✅ Core Python Modules (`/python/comfy_bridge/`)
```
python/comfy_bridge/
├── __init__.py              [11 lines]  - Package initialization, exports ComfyAPI & ComfyWorkflowParser
├── comfy_api.py            [289 lines] - ✅ ComfyUI REST API client (WORKING)
└── comfy_parser.py         [503 lines] - ✅ Workflow parser with format conversion (WORKING)
```

**Status:** Core modules are functional and well-structured.

#### ✅ HDA Scripts (`/scripts/`)
```
scripts/
├── hda_execute_workflow.py [351 lines] - ⚠️  Main HDA execution script (PARTIALLY WORKING)
├── comfy_cop_node.py       [349 lines] - 🔧 COP node class implementation (UNUSED - for reference)
└── build_hda.py            [143 lines] - 🔧 HDA builder script (DEVELOPMENT TOOL)
```

**Issues:**
- `hda_execute_workflow.py` - Latest version with direct file reading NOT loaded into HDA yet
- `comfy_cop_node.py` - Appears to be unused, HDA uses inline PythonModule instead
- `build_hda.py` - Works but HDA path hardcoded to `~/houdini*/otls/`

#### ✅ HDA Files (`/otls/`)
```
otls/
├── comfyui_bridge.hda       [5.7KB]  - ✅ Current HDA (v38 based on backup count)
└── backup/
    └── comfyui_bridge_bak*.hda [38 files, 947B - 5.7KB] - 🗑️  REDUNDANT
```

**Issues:**
- **38 backup files** consuming 175KB of space
- No backup rotation/cleanup strategy
- Backups likely created by Houdini automatically

#### ✅ Documentation
```
├── README.md                [9.4KB]  - ✅ Comprehensive project documentation
├── QUICKSTART.md            [4.6KB]  - ✅ Getting started guide
├── HOUDINI_API_REFERENCE.md [1.6KB]  - ✅ Houdini API discoveries & gotchas
└── LICENSE                  [1.1KB]  - ✅ MIT License
```

**Status:** Documentation is good but needs updates for current state.

#### ✅ Examples
```
examples/
└── example_workflow.json    [81 lines] - ✅ Sample workflow in API format
```

**Status:** Good reference workflow.

#### ✅ Tests
```
tests/
├── run_tests.py             [54 lines]  - ✅ Test runner
├── test_api.py             [121 lines] - ✅ API tests (passing)
└── test_parser.py          [253 lines] - ✅ Parser tests (passing)
```

**Status:** Good test coverage for core modules.

#### 🗑️ Empty/Unused Directories
```
houdini/otls/               - EMPTY (no files)
otls/backup/                - 38 HDA backups (should be cleaned)
__pycache__/                - 3 locations (gitignored but present)
```

### 1.2 External Test Files (Home Directory)

**Found in `/home/maxborg/`:**
```
test_image_upload.py        [1.8KB]  - ✅ Test script created today
test_retrieve_image.py      [1.3KB]  - ⚠️  Old test with hardcoded prompt_id
```

**Found in `/tmp/`:**
```
workflow_debug.json         [2.2KB]  - 🔍 Latest workflow sent to ComfyUI
comfyui_payload_debug.json  [2.2KB]  - 🔍 Latest API payload
```

**Status:** Debug files useful for troubleshooting, test scripts should be moved to `/tests/`.

### 1.3 Duplicate/Conflicting Code

#### ⚠️  ISSUE: Two Execution Implementations

**File:** `scripts/comfy_cop_node.py` (349 lines)
- Contains `ComfyCOPNode` class with full UI and execution logic
- **NOT USED** - HDA uses inline PythonModule code instead

**File:** `scripts/hda_execute_workflow.py` (351 lines)
- Contains standalone `execute_workflow()` function
- **ACTIVELY USED** - Embedded in HDA's PythonModule section
- Handles workflow execution, image I/O, parameter mapping

**Problem:**
- Confusing which file is authoritative
- `comfy_cop_node.py` has cleaner OOP structure but isn't used
- `hda_execute_workflow.py` is procedural and duplicates some logic

**Recommendation:** Decide on one approach - either:
1. Use `comfy_cop_node.py` class in HDA PythonModule (cleaner)
2. Delete `comfy_cop_node.py` and keep procedural approach (simpler)

### 1.4 Configuration Issues

#### ❌ Missing Configuration
- No `houdini.env` file in repository (expected in user's `~/houdini21.0/`)
- No setup script to configure paths automatically
- README assumes user will manually edit `houdini.env`

#### ❌ Hardcoded Paths
Found in multiple files:
```python
# hda_execute_workflow.py:12
bridge_path = '/home/maxborg/houdini-comfy-bridge/python'

# test files
sys.path.insert(0, '/home/maxborg/houdini-comfy-bridge/python')
```

**Impact:** Code won't work on other machines without editing.

#### ❌ .gitignore Issues
- **Missing:** `otls/backup/` should be ignored (currently committed)
- **Missing:** `/tmp/` debug files
- **Missing:** Test output files
- **Has:** Standard Python/Houdini ignores ✅

---

## 2. CURRENT STATE SUMMARY

### 2.1 What's Working ✅

#### Core Functionality (Tested & Confirmed)
1. **ComfyUI API Connection** ✅
   - `comfy_api.py:is_server_alive()` - Server health checks
   - `comfy_api.py:queue_prompt()` - Workflow queuing
   - `comfy_api.py:wait_for_completion()` - Execution monitoring
   - `comfy_api.py:get_image()` - Image download

2. **Workflow Parsing** ✅
   - `comfy_parser.py:load_workflow()` - JSON loading
   - `comfy_parser.py:_convert_to_api_format()` - Frontend→API conversion
   - `comfy_parser.py:_extract_input_nodes()` - INPUT_ node detection
   - `comfy_parser.py:get_input_parameters()` - Parameter generation

3. **Format Conversion** ✅
   - Converts ComfyUI frontend format (nodes array) to API format (node dict)
   - Handles widget value type matching (INT, FLOAT, STRING, COMBO)
   - Preserves node connections via link mapping

4. **Workflow Execution** ✅
   - Sends workflow to ComfyUI `/prompt` endpoint
   - Polls for completion with timeout
   - Returns list of (filename, image_bytes) tuples

### 2.2 What's Failing ❌

#### Critical Issues

**1. Input Image Not Being Read** ❌
- **File:** `hda_execute_workflow.py:212-288`
- **Function:** `_read_cop_image_as_png()`
- **Issue:** Multiple failed attempts to read COP node output:
  - ❌ Attempt 1: `cop_node.saveImage()` - Method doesn't exist
  - ❌ Attempt 2: Create ROP Composite node - Invalid context
  - ❌ Attempt 3: `hou.hscript("icopoutput")` - Command doesn't exist in Houdini 21
  - ⚠️  Attempt 4: Read File COP source directly - **NOT TESTED YET**

**Current Code (Lines 232-253):**
```python
if cop_node.type().name() == 'file':
    file_path_parm = cop_node.parm('filename1')
    if file_path_parm:
        file_path = file_path_parm.evalAsString()
        file_path = hou.text.expandString(file_path)

        if os.path.exists(file_path):
            print(f"Reading directly from File COP source: {file_path}")
            pil_image = Image.open(file_path)
            # ... convert and return PNG bytes
```

**Status:** Code updated but NOT loaded into HDA yet.

**2. Output Image Not Displayed in Houdini** ⚠️
- **File:** `hda_execute_workflow.py:290-350`
- **Function:** `_write_png_to_cop()`
- **Issue:** HDA is locked, can't create internal File node
- **Current Behavior:** Saves to `~/comfyui_output/` instead
- **Problem:** User must manually load output in separate File COP node

**3. HDA Code Not Updated** ❌
- **Issue:** Latest fixes in `hda_execute_workflow.py` NOT in HDA PythonModule
- **Evidence:** User's error logs show old `icopoutput` code running
- **Impact:** All recent fixes ineffective until HDA is updated

### 2.3 Root Causes of Recurring Issues

#### 🔍 Issue Pattern #1: "AttributeError: 'str' object has no attribute 'get'"

**Root Cause:** Workflow data structure inconsistency

**Where it happens:**
1. `comfy_parser.py:216-223` - `_extract_input_nodes()`
2. `comfy_parser.py:427-432` - `update_workflow_inputs()`
3. `hda_execute_workflow.py:146-154` - Debug printing

**Why it happens:**
- Some workflow nodes are strings instead of dicts after conversion
- Frontend format conversion doesn't handle all edge cases
- Malformed workflow JSON from ComfyUI exports

**Evidence from code:**
```python
# hda_execute_workflow.py:150-153
for node_id, node_data in list(updated_workflow.items())[:3]:
    if isinstance(node_data, dict):  # ← Type check added
        print(f"  Node {node_id}: {node_data.get('class_type', 'unknown')}")
    else:
        print(f"  Node {node_id}: {type(node_data)} - {node_data}")
```

**Fixed by:** Type checking before `.get()` calls (Lines 221, 430, 150)

#### 🔍 Issue Pattern #2: Houdini API Method Failures

**Root Cause:** Undocumented/version-specific Houdini API

**Examples:**
1. `cop_node.saveImage()` - Doesn't exist (any version)
2. `cop_node.xRes()`, `yRes()` - Don't exist on File nodes
3. `hou.hscript("icopoutput")` - Removed in Houdini 21

**Why it happens:**
- Houdini's COP API is minimally documented
- COP2 nodes have limited direct pixel access
- API changes between Houdini versions without deprecation notices

**Solution Approach:**
1. Test API methods before using
2. Document findings in `HOUDINI_API_REFERENCE.md`
3. Use workarounds (direct file I/O instead of COP pixel access)

#### 🔍 Issue Pattern #3: Module Import/Reload Problems

**Root Cause:** Houdini doesn't auto-reload Python modules

**Evidence:**
- User's error logs show old code (`icopoutput`) despite file updates
- HDA PythonModule is cached in memory

**Why it happens:**
1. User edits `scripts/hda_execute_workflow.py` ✅
2. File is saved ✅
3. HDA still has old PythonModule code in memory ❌
4. User must manually reload HDA or restart Houdini ❌

**Solution:**
- Document HDA update process clearly
- Consider auto-reload mechanism in development
- Use external scripts for rapid iteration

---

## 3. RESTRUCTURE PROPOSAL

### 3.1 Recommended Folder Structure

```
houdini-comfy-bridge/
├── README.md
├── QUICKSTART.md
├── HOUDINI_API_REFERENCE.md
├── LICENSE
├── .gitignore                          [UPDATED]
│
├── python/                             [Core library]
│   └── comfy_bridge/
│       ├── __init__.py
│       ├── comfy_api.py               ✅ Keep
│       └── comfy_parser.py            ✅ Keep
│
├── houdini/                            [Houdini integration]
│   ├── scripts/                       [HDA Python modules]
│   │   └── comfy_bridge_module.py    [RENAMED from hda_execute_workflow.py]
│   ├── otls/
│   │   └── comfy_bridge.hda          ✅ Keep (production HDA)
│   └── toolbar/                       [NEW - shelf tools]
│       └── comfy_bridge.shelf
│
├── examples/                           [Example workflows]
│   ├── example_workflow.json         ✅ Keep
│   └── img2img_workflow.json         [NEW - when implemented]
│
├── tests/                              [Unit tests]
│   ├── run_tests.py                  ✅ Keep
│   ├── test_api.py                   ✅ Keep
│   ├── test_parser.py                ✅ Keep
│   └── test_integration.py           [NEW - HDA integration tests]
│
├── tools/                              [Development tools]
│   ├── build_hda.py                  [MOVED from scripts/]
│   └── update_hda_module.py          [NEW - auto-update HDA PythonModule]
│
└── dev/                                [Development/debug files]
    ├── test_image_upload.py          [MOVED from ~/]
    └── test_retrieve_image.py        [MOVED from ~/]
```

### 3.2 Files to Delete 🗑️

#### High Priority - Delete Immediately
```
otls/backup/comfyui_bridge_bak*.hda   [38 files] - Git history is sufficient
houdini/otls/                          [empty dir]  - Remove empty directory
scripts/comfy_cop_node.py              [349 lines] - Unused reference code
```

**Estimated space saved:** ~180KB + reduced confusion

#### Medium Priority - Clean After Migration
```
/home/maxborg/test_image_upload.py    → Move to tests/dev/
/home/maxborg/test_retrieve_image.py  → Move to tests/dev/
/tmp/workflow_debug.json               → Delete (regenerated as needed)
/tmp/comfyui_payload_debug.json        → Delete (regenerated as needed)
```

### 3.3 Files to Consolidate

#### Option A: Keep Procedural Style (Simpler)
```
Action: DELETE scripts/comfy_cop_node.py
Reason: HDA uses hda_execute_workflow.py directly
Benefit: Less confusion, clearer code path
```

#### Option B: Migrate to OOP Style (Cleaner)
```
Action: MERGE hda_execute_workflow.py → comfy_cop_node.py
Steps:
  1. Port image I/O functions to ComfyCOPNode class
  2. Update HDA PythonModule to use ComfyCOPNode
  3. Delete hda_execute_workflow.py
Benefit: Better structure, easier to test
```

**Recommendation:** **Option A** - Keep it simple, working code first, refactor later.

### 3.4 Better Organization for Pipeline Use

#### For Studio/Production Use

**Recommended Structure:**
```
/studio/pipeline/houdini/
├── otls/
│   └── comfy_bridge.hda              [Production HDA]
├── packages/
│   └── comfy_bridge.json             [Houdini package file]
└── python/
    └── comfy_bridge/                 [Python module]
```

**Create `comfy_bridge.json` Package File:**
```json
{
    "env": [
        {
            "COMFY_BRIDGE_ROOT": "$HOUDINI_PACKAGE_PATH/comfy_bridge"
        },
        {
            "PYTHONPATH": {
                "value": "$COMFY_BRIDGE_ROOT/python",
                "method": "prepend"
            }
        },
        {
            "HOUDINI_OTLSCAN_PATH": {
                "value": "$COMFY_BRIDGE_ROOT/otls",
                "method": "prepend"
            }
        }
    ]
}
```

**Benefits:**
- No manual `houdini.env` editing
- Version-controlled environment
- Easy to deploy across machines
- Clean uninstall (delete package folder)

---

## 4. ISSUE ANALYSIS

### 4.1 Why We Keep Hitting 'str' object has no attribute 'get' Errors

#### Root Cause: Workflow Format Ambiguity

**ComfyUI has TWO export formats:**

1. **Frontend Format** (from "Save" button):
```json
{
  "nodes": [
    {
      "id": 1,
      "type": "LoadImage",
      "widgets_values": ["image.png"]
    }
  ],
  "links": [[0, 1, 0, 2, 1, "IMAGE"]],
  "version": 0.4
}
```

2. **API Format** (from "Save (API Format)" button):
```json
{
  "1": {
    "class_type": "LoadImage",
    "inputs": {
      "image": "image.png"
    }
  }
}
```

**The Problem:**
- Parser expects API format (dict with node IDs as keys)
- Some ComfyUI workflows export in frontend format (nodes array)
- Conversion code (`_convert_to_api_format`) sometimes produces mixed types
- Code tries to call `.get()` on strings → `AttributeError`

**Where it happens:**
```python
# comfy_parser.py:226
class_type = node_data.get('class_type', '')  # ← Fails if node_data is string

# hda_execute_workflow.py:151
print(f"  Node {node_id}: {node_data.get('class_type', 'unknown')}")  # ← Same issue
```

**The Fix Applied:**
```python
# Type checking before .get()
if isinstance(node_data, dict):
    class_type = node_data.get('class_type', '')
else:
    print(f"Skipping non-dict node: {node_data}")
    continue
```

**Locations Fixed:**
- ✅ `comfy_parser.py:221` - `_extract_input_nodes()`
- ✅ `comfy_parser.py:430` - `update_workflow_inputs()`
- ✅ `hda_execute_workflow.py:150` - Debug printing

**Why It STILL Might Happen:**
- If workflow has malformed JSON
- If conversion logic has edge cases not covered
- If ComfyUI changes export format

**Prevention Strategy:**
1. Always use "Save (API Format)" in ComfyUI ✅
2. Validate workflow structure before processing
3. Add comprehensive type checking throughout

### 4.2 Why Houdini API Methods Keep Failing

#### Root Cause: Sparse Documentation + Version Changes

**The Houdini COP2 API Problem:**

Houdini's COP (Compositor) nodes have **limited programmatic access** compared to SOP/DOP/ROP nodes.

**Methods That DON'T Exist:**
```python
cop_node.saveImage()      # ❌ Not a real method
cop_node.xRes()           # ❌ Only on some node types
cop_node.yRes()           # ❌ Only on some node types
cop_node.allPixels()      # ❌ Doesn't work on File/output nodes
```

**Houdini 21 Specific Issues:**
```python
hou.hscript("icopoutput")  # ❌ Removed in Houdini 21
hou.hscript("mwrite")      # ⚠️  Works but requires X11 (no headless)
```

**What DOES Work:**
```python
# Parameter access
parm.evalAsString()        # ✅ For string parameters
parm.eval()                # ✅ For int/float parameters

# Node queries
cop_node.type().name()     # ✅ Get node type
cop_node.parm('filename1') # ✅ Access parameters
cop_node.cook(force=True)  # ✅ Force evaluation

# File operations
hou.text.expandString()    # ✅ Expand $HIP, $F, etc.
```

**Why This Keeps Happening:**
1. **SideFX Documentation Gaps** - COP API poorly documented
2. **Version Fragmentation** - Methods removed without deprecation warnings
3. **Trial and Error Required** - No way to know what works without testing

**Solution:**
- Maintain `HOUDINI_API_REFERENCE.md` with tested methods ✅
- Use workarounds (file I/O instead of pixel access) ✅
- Test on target Houdini version before deployment ✅

### 4.3 Module Import/Reload Problems

#### Root Cause: Houdini's Python Module Caching

**The Problem:**

```
1. User edits scripts/hda_execute_workflow.py
2. Houdini HDA still has OLD PythonModule in memory
3. User runs HDA → OLD CODE EXECUTES
4. User sees error logs with OLD CODE (icopoutput)
5. User is confused why fixes aren't working
```

**Why Houdini Caches:**
- HDA PythonModule is embedded in `.hda` file
- Changing external `.py` file doesn't update HDA
- HDA must be explicitly updated via Type Properties dialog

**Current Workflow (Manual):**
```
1. Edit scripts/hda_execute_workflow.py
2. Open Houdini
3. Right-click node → Type Properties
4. Go to Scripts → PythonModule
5. Copy/paste entire file content
6. Click Accept → Apply
7. Test changes
```

**This Is Error-Prone Because:**
- ❌ Easy to forget step 3-6
- ❌ No version tracking (which HDA has which code?)
- ❌ Manual process breaks automation

**Solution Options:**

**Option 1: External Script Reference (Recommended)**
```python
# In HDA PythonModule:
import sys
sys.path.insert(0, '/path/to/houdini-comfy-bridge/python')
from comfy_bridge_hda import execute_workflow

def execute_workflow_callback(node):
    execute_workflow(node)  # Calls external module
```

**Benefits:**
- ✅ Auto-reloads when file changes (with `importlib.reload()`)
- ✅ Version controlled in git
- ✅ Easier to test

**Option 2: Auto-Update Tool**
```python
# tools/update_hda_module.py
def update_hda_pythonmodule():
    hda_path = '/path/to/comfy_bridge.hda'
    script_path = '/path/to/comfy_bridge_module.py'

    # Read script content
    with open(script_path) as f:
        code = f.read()

    # Update HDA definition
    hda_def = hou.hda.definitionsInFile(hda_path)[0]
    sections = hda_def.sections()
    sections['PythonModule'].setContents(code)
```

**Option 3: Development Mode**
```python
# Add to HDA PythonModule for development:
import importlib
import sys

# Force reload on each execution
if 'comfy_bridge_hda' in sys.modules:
    importlib.reload(sys.modules['comfy_bridge_hda'])
```

**Recommendation:** Use **Option 1** (external reference) for development, embed for production release.

---

## 5. ACTION PLAN

### 5.1 Immediate Fixes (Critical Path)

#### Phase 1: Update HDA with Latest Code ⚡ HIGH PRIORITY

**Goal:** Get current fixes into production HDA

**Steps:**
1. ✅ Verify `hda_execute_workflow.py` has latest fixes (already done)
2. Open Houdini
3. Load HDA: Right-click node → Type Properties
4. Go to: Scripts tab → PythonModule section
5. Replace entire content with `scripts/hda_execute_workflow.py`
6. Click: Accept → Apply → Save HDA

**Testing:**
```python
# After update, run in Houdini:
node = hou.node('/img/cop2net1/comfyui_bridge1')
node.parm('execute').pressButton()
# Check console for "Reading directly from File COP source:" message
```

**Success Criteria:**
- ✅ No `icopoutput` errors
- ✅ Input image reads from File COP
- ✅ Workflow executes
- ✅ Output saves (even if to ~/comfyui_output/)

**Estimated Time:** 10 minutes

---

#### Phase 2: Test Input Image Upload 🧪 HIGH PRIORITY

**Goal:** Verify File COP reading works

**Prerequisites:**
- Phase 1 complete
- ComfyUI running
- Test image file exists

**Test Procedure:**
```
1. In Houdini COP network:
   - Create File COP node
   - Load test image (e.g., 512x512 PNG)
   - Connect to ComfyUI Bridge input

2. Set ComfyUI Bridge parameters:
   - Workflow: /path/to/workflow_debug.json
   - Server: 127.0.0.1:8188

3. Click Execute Workflow

4. Check console output for:
   ✓ "Reading directly from File COP source: /path/to/image.png"
   ✓ "Read XXXX bytes from input COP"
   ✓ "Uploaded input image: {...}"
   ✓ "Received N output image(s)"
```

**If it fails:**
- Check file path is valid
- Check image file exists
- Check PIL/Pillow is available in Houdini Python
- Add debug print statements

**Success Criteria:**
- ✅ Image uploaded to ComfyUI
- ✅ Workflow uses uploaded image (not cached)
- ✅ New output generated

**Estimated Time:** 15 minutes

---

#### Phase 3: Fix Output Display 🖼️ MEDIUM PRIORITY

**Goal:** Display output in Houdini COP network (not just save to file)

**Current Issue:**
- HDA is locked → can't create internal File node
- Output saves to ~/comfyui_output/ instead

**Solution Options:**

**Option A: Unlock HDA (Quick)**
```
1. Right-click HDA → Type Properties
2. Go to: Basic tab
3. Uncheck: "Lock Contents"
4. Click Apply
5. Code can now create internal File node
```

**Option B: Use Output Node (Better)**
```
1. User creates File COP outside HDA
2. Set File node path: $HIP/output/comfy_output_$F4.png
3. Connect ComfyUI Bridge → File node
4. HDA sets File path parameter programmatically
```

**Option C: Create Output Parameter (Best)**
```python
# In HDA parameters, add:
output_path = hou.StringParmTemplate(
    'output_path', 'Output Path',
    1, default_value=('$HIP/comfy_output/output_$F4.png',)
)

# In _write_png_to_cop():
output_path = node.parm('output_path').evalAsString()
expanded_path = hou.text.expandString(output_path)
with open(expanded_path, 'wb') as f:
    f.write(png_data)
print(f"Saved output to: {expanded_path}")
```

**Recommendation:** Use **Option C** - gives user control, works with locked HDA.

**Estimated Time:** 30 minutes

---

### 5.2 Code Quality Improvements 🔧 MEDIUM PRIORITY

#### Task 1: Remove Unused Code

**Delete:**
```bash
rm scripts/comfy_cop_node.py                    # 349 lines unused
rm -rf otls/backup/comfyui_bridge_bak*.hda     # 38 backup files
rmdir houdini/otls                              # Empty directory
```

**Update `.gitignore:`
```bash
echo "otls/backup/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "/tmp/" >> .gitignore
```

**Estimated Time:** 5 minutes

---

#### Task 2: Move Test Files

**Organize:**
```bash
mkdir -p dev/
mv ~/test_image_upload.py dev/
mv ~/test_retrieve_image.py dev/
```

**Update import paths:**
```python
# In dev/test_*.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
```

**Estimated Time:** 10 minutes

---

#### Task 3: Fix Hardcoded Paths

**Files to update:**
- `scripts/hda_execute_workflow.py:12`
- `dev/test_image_upload.py:5`
- `dev/test_retrieve_image.py:5`

**Solution:**
```python
# Instead of:
bridge_path = '/home/maxborg/houdini-comfy-bridge/python'

# Use:
import os
bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
if bridge_path not in sys.path:
    sys.path.insert(0, bridge_path)
```

**Or better (for HDA):**
```python
# Let houdini.env handle PYTHONPATH, just import:
try:
    from comfy_bridge import ComfyAPI, ComfyWorkflowParser
except ImportError:
    # Fallback for development
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
    from comfy_bridge import ComfyAPI, ComfyWorkflowParser
```

**Estimated Time:** 15 minutes

---

### 5.3 Documentation Updates 📚 LOW PRIORITY

#### Task 1: Update README.md

**Sections to update:**
1. Roadmap → Mark "Input image support" as ✅ DONE
2. Installation → Add Houdini package method
3. Troubleshooting → Add "HDA not updating" section

**Estimated Time:** 20 minutes

---

#### Task 2: Create Setup Guide

**New file:** `SETUP.md`

**Content:**
```markdown
# Setup Guide

## Method 1: Houdini Package (Recommended)

1. Copy repository to: `/path/to/houdini-comfy-bridge`
2. Create package file: `~/houdini21.0/packages/comfy_bridge.json`
3. Add content: [package JSON]
4. Restart Houdini

## Method 2: Manual houdini.env

[Current README instructions]

## Updating HDA Code

When you update scripts/hda_execute_workflow.py:
1. Open Houdini
2. Right-click node → Type Properties
3. Scripts → PythonModule
4. Copy/paste updated code
5. Accept → Apply

## Development Mode

For rapid iteration without HDA updates:
[External script reference method]
```

**Estimated Time:** 30 minutes

---

#### Task 3: Update HOUDINI_API_REFERENCE.md

**Add sections:**
```markdown
## COP Image I/O

### Reading Images
- ✅ File COP: Read source file via `parm('filename1').evalAsString()`
- ❌ Other COPs: No direct pixel access available
- ⚠️  Workaround: Save to temp file first

### Writing Images
- ✅ Create File COP node, set path parameter
- ❌ Can't write pixels directly to COP output
- ⚠️  If HDA locked: Save to external file, user loads manually
```

**Estimated Time:** 15 minutes

---

### 5.4 Priority Order & Timeline

#### Week 1: Critical Path (Get It Working)

| Day | Task | Priority | Time | Status |
|-----|------|----------|------|--------|
| 1 | Phase 1: Update HDA with latest code | 🔴 Critical | 10m | Pending |
| 1 | Phase 2: Test input image upload | 🔴 Critical | 15m | Pending |
| 1 | Phase 3: Fix output display | 🟡 High | 30m | Pending |
| 2 | Test end-to-end workflow | 🔴 Critical | 1h | Pending |
| 2 | Fix any bugs found in testing | 🔴 Critical | 2h | Pending |

**Total Week 1:** ~4 hours

#### Week 2: Code Quality

| Day | Task | Priority | Time | Status |
|-----|------|----------|------|--------|
| 3 | Remove unused code | 🟢 Medium | 5m | Pending |
| 3 | Move test files | 🟢 Medium | 10m | Pending |
| 3 | Fix hardcoded paths | 🟡 High | 15m | Pending |
| 4 | Update .gitignore | 🟢 Medium | 5m | Pending |
| 4 | Create Houdini package file | 🟢 Medium | 30m | Pending |
| 5 | Test package installation | 🟢 Medium | 30m | Pending |

**Total Week 2:** ~2 hours

#### Week 3: Documentation & Polish

| Day | Task | Priority | Time | Status |
|-----|------|----------|------|--------|
| 6 | Update README.md | 🔵 Low | 20m | Pending |
| 6 | Create SETUP.md | 🔵 Low | 30m | Pending |
| 7 | Update HOUDINI_API_REFERENCE.md | 🔵 Low | 15m | Pending |
| 7 | Add integration tests | 🟢 Medium | 2h | Pending |

**Total Week 3:** ~3 hours

---

## 6. SUMMARY & RECOMMENDATIONS

### 6.1 Critical Actions (Do First)

1. **Update HDA PythonModule** with latest `hda_execute_workflow.py`
   - User's errors show old code still running
   - All recent fixes ineffective until this is done

2. **Test input image upload**
   - Code is ready (direct File COP reading)
   - Needs real-world testing to confirm

3. **Fix output display**
   - Current workaround (save to file) is functional but clunky
   - Add output path parameter for user control

### 6.2 Structural Issues to Address

1. **Duplicate implementations** - Remove `comfy_cop_node.py` or migrate to it
2. **38 backup HDAs** - Delete, use git history instead
3. **Hardcoded paths** - Replace with relative/environment paths
4. **No package file** - Create for easier deployment

### 6.3 Process Improvements

1. **HDA Development Workflow:**
   - Use external script reference during development
   - Embed code for production release
   - Document update process clearly

2. **Testing:**
   - Add integration tests for HDA functionality
   - Test on clean Houdini install
   - Verify on other machines/users

3. **Documentation:**
   - Keep HOUDINI_API_REFERENCE.md updated with discoveries
   - Add troubleshooting guide for common issues
   - Include setup automation (package file)

### 6.4 Long-term Considerations

**For Production Use:**
- Consider external dependency management (PIL/Pillow)
- Add error recovery (retry on network failures)
- Implement progress feedback (progress bar)
- Add batch processing support

**For Open Source Release:**
- Remove hardcoded paths (all locations)
- Add CI/CD for automated testing
- Create installation script
- Add example video/tutorial

---

## APPENDIX A: Quick Reference

### File Locations
```
Core Library:     python/comfy_bridge/
HDA Script:       scripts/hda_execute_workflow.py
Production HDA:   otls/comfy_bridge.hda
Tests:            tests/
Documentation:    *.md files
```

### Common Commands
```bash
# Run tests
cd /path/to/houdini-comfy-bridge
python tests/run_tests.py

# Test API connection
python dev/test_image_upload.py

# Update HDA (automated)
python tools/update_hda_module.py
```

### Debug Locations
```
Workflow debug:   /tmp/workflow_debug.json
API payload:      /tmp/comfyui_payload_debug.json
Output images:    ~/comfyui_output/
```

---

**End of Audit Report**
