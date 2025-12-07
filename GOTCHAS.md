# Gotchas, Pitfalls & Lessons Learned

**Last Updated:** 2025-12-07

This document captures common mistakes, surprising behaviors, and hard-learned lessons from developing the Houdini-ComfyUI Bridge.

---

## Houdini API Gotchas

### 1. Parameter Evaluation - Wrong Method = Wrong Type

**THE GOTCHA:**
```python
# This looks harmless but causes MAJOR bugs:
server_address = node.parm('server_address').eval()  # ❌ WRONG

# "127.0.0.1:8188" gets evaluated as Python expression!
# Result: Tries to parse as float subtraction: 127.0.1 - 8188
```

**THE FIX:**
```python
# String parameters - ALWAYS use evalAsString()
server_address = node.parm('server_address').evalAsString()  # ✅ CORRECT

# Int/Float parameters - use eval()
port = node.parm('comfy_port').eval()  # ✅ CORRECT for numbers
```

**WHY IT HAPPENS:**
- `eval()` treats parameter as Python expression
- `evalAsString()` returns literal string value
- Houdini doesn't warn you when you use the wrong one
- Bugs are silent and confusing

**LESSON:** Match evaluation method to parameter template type, always.

---

### 2. HDA Code Caching - Your Edits Disappear

**THE GOTCHA:**
```
1. You edit scripts/hda_execute_workflow.py
2. You save the file ✅
3. You run the HDA in Houdini
4. OLD CODE EXECUTES ❌
5. You think you're going crazy 🤯
```

**WHY IT HAPPENS:**
- HDA PythonModule code is **embedded in .hda file**
- Editing external .py files doesn't update the .hda
- HDA caches code in memory, doesn't reload
- No warning, no error, just old code running

**THE FIX:**
```
Manual update process:
1. Right-click HDA → Type Properties
2. Scripts tab → PythonModule section
3. Copy scripts/hda_execute_workflow.py content
4. Paste into PythonModule (replace all)
5. Accept → Apply → Save Node Type
```

**BETTER FIX (Development):**
```python
# In HDA PythonModule, use external reference:
import importlib
import sys
sys.path.insert(0, '/path/to/python')

# Force reload on each execution
if 'hda_execute_workflow' in sys.modules:
    importlib.reload(sys.modules['hda_execute_workflow'])

from hda_execute_workflow import execute_workflow
```

**LESSON:** Never trust that your code changes are running until you verify the HDA was updated.

---

### 3. Deprecated Commands Fail Silently

**THE GOTCHA:**
```python
# This worked in Houdini 19.5:
hou.hscript("icopoutput -d /tmp/out.png -f 1 1 /img/cop2net1/file1")

# In Houdini 21:
# RuntimeError: Unknown command: icopoutput
```

**WHY IT HAPPENS:**
- SideFX removes commands without deprecation warnings
- No compile-time errors (it's a string)
- Documentation often doesn't mention removal
- No version compatibility flags

**THE FIX:**
```python
# Don't use icopoutput - use direct file I/O instead
if cop_node.type().name() == 'file':
    file_path = cop_node.parm('filename1').evalAsString()
    pil_image = Image.open(file_path)  # Direct file read
```

**OTHER DEPRECATED COMMANDS:**
- `icopoutput` - Removed in Houdini 21
- `mwrite` - Still exists but requires X11 (fails headless)

**LESSON:** Never use hscript commands if a Python API alternative exists. If you must use hscript, wrap in version check.

---

### 4. COP Node Methods That Don't Exist

**THE GOTCHA:**
```python
# These look like they should exist, but don't:
cop_node.saveImage('/tmp/out.png')     # ❌ AttributeError
cop_node.xRes()                        # ❌ Only on some node types
cop_node.yRes()                        # ❌ Only on some node types
cop_node.allPixels()                   # ❌ Doesn't work on File nodes
```

**WHY IT HAPPENS:**
- COP2 API is underdocumented
- Different node types have different methods
- No comprehensive API reference
- Trial and error required

**WHAT ACTUALLY WORKS:**
```python
# These DO work:
cop_node.type().name()                 # ✅ Get node type
cop_node.parm('filename1')             # ✅ Access parameters
cop_node.cook(force=True)              # ✅ Force evaluation
hou.text.expandString(path)            # ✅ Expand $HIP, $F, etc.
```

**LESSON:** Test every Houdini API method before relying on it. Document what works in HOUDINI_API_REFERENCE.md.

---

## ComfyUI Workflow Gotchas

### 5. Frontend vs API Format Confusion

**THE GOTCHA:**
```python
# You think workflow is a dict like this:
workflow = {"1": {"class_type": "...", "inputs": {...}}}

# But sometimes it's actually this:
workflow = {"nodes": [...], "links": [...], "version": 0.4}

# Your code does:
class_type = workflow["1"]["class_type"]  # ❌ KeyError
```

**WHY IT HAPPENS:**
- ComfyUI has TWO export formats
- "Save" button → Frontend format (nodes array)
- "Save (API Format)" button → API format (node dict)
- Format not indicated in file

**THE FIX:**
```python
# Always check format and convert:
if 'nodes' in workflow_data:
    # Frontend format - convert to API
    workflow_data = self._convert_to_api_format(workflow_data)

# Now safe to use:
class_type = workflow_data["1"]["class_type"]  # ✅ Works
```

**LESSON:** Never assume workflow format. Always detect and convert.

---

### 6. 'str' object has no attribute 'get'

**THE GOTCHA:**
```python
# This crashes mysteriously:
for node_id, node_data in workflow.items():
    class_type = node_data.get('class_type', '')  # ❌ AttributeError

# Error: 'str' object has no attribute 'get'
```

**WHY IT HAPPENS:**
- Format conversion sometimes produces mixed types
- Some nodes end up as strings instead of dicts
- No type validation before .get() call

**THE FIX:**
```python
# ALWAYS type check before .get():
for node_id, node_data in workflow.items():
    if not isinstance(node_data, dict):
        print(f"Skipping non-dict node: {node_id}")
        continue
    class_type = node_data.get('class_type', '')  # ✅ Safe
```

**WHERE IT HAPPENS:**
- comfy_parser.py:221 (`_extract_input_nodes()`)
- comfy_parser.py:430 (`update_workflow_inputs()`)
- hda_execute_workflow.py:150 (debug printing)

**LESSON:** Always validate types before calling dict methods.

---

## Image Processing Gotchas

### 7. RGBA vs RGB Color Modes

**THE GOTCHA:**
```python
# You upload PNG with alpha channel:
pil_image = Image.open('input.png')  # RGBA mode
png_buffer = io.BytesIO()
pil_image.save(png_buffer, format='PNG')

# ComfyUI workflow expects RGB
# Workflow fails with dimension mismatch error
```

**WHY IT HAPPENS:**
- PNG files often have alpha channel (RGBA)
- ComfyUI models expect 3-channel RGB
- PIL saves in original mode unless told otherwise

**THE FIX:**
```python
pil_image = Image.open('input.png')

# Always convert to RGB:
if pil_image.mode == 'RGBA':
    pil_image = pil_image.convert('RGB')  # ✅ Remove alpha

png_buffer = io.BytesIO()
pil_image.save(png_buffer, format='PNG')
```

**LESSON:** Always normalize image color mode before processing.

---

### 8. File Paths Need Expansion

**THE GOTCHA:**
```python
# User sets output path to:
"$HIP/renders/output.png"

# You use it directly:
with open(output_path, 'wb') as f:  # ❌ FileNotFoundError
    f.write(data)

# Error: No such file or directory: '$HIP/renders/output.png'
```

**WHY IT HAPPENS:**
- Houdini variables ($HIP, $F, $OS) are not environment variables
- Python's open() doesn't expand Houdini variables
- Looks like a path but isn't expanded

**THE FIX:**
```python
# ALWAYS expand Houdini variables:
output_path = node.parm('output_path').evalAsString()
expanded_path = hou.text.expandString(output_path)  # ✅ Expands $HIP

# Now it works:
with open(expanded_path, 'wb') as f:
    f.write(data)
```

**COMMON VARIABLES:**
- `$HIP` - Project directory
- `$F` - Current frame number
- `$F4` - Frame number, padded to 4 digits
- `$OS` - Node name

**LESSON:** Expand all file paths from parameters before using.

---

## Development Workflow Gotchas

### 9. Hardcoded Paths Break on Other Machines

**THE GOTCHA:**
```python
# You write:
sys.path.insert(0, '/home/maxborg/houdini-comfy-bridge/python')

# Works on your machine ✅
# Fails on every other machine ❌
# You forget to fix it before committing
```

**WHY IT HAPPENS:**
- Easy to write during development
- Works immediately on your machine
- No error until someone else tries to use it
- Hard to catch in review

**THE FIX:**
```python
# Use relative paths:
import os
bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
bridge_path = os.path.abspath(bridge_path)
sys.path.insert(0, bridge_path)
```

**OR BETTER:**
```python
# Rely on PYTHONPATH from houdini.env:
try:
    from comfy_bridge import ComfyAPI
except ImportError:
    # Fallback for development
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
    from comfy_bridge import ComfyAPI
```

**LESSON:** Never commit hardcoded paths. Use relative paths or environment variables.

---

### 10. Git Doesn't Track Binary .hda Changes Well

**THE GOTCHA:**
```
You update HDA in Houdini
Git sees .hda file changed
Diff shows: "Binary file changed"
No way to see what changed
Can't review code changes
Can't merge conflicts
```

**WHY IT HAPPENS:**
- .hda files are binary format
- Git can't diff binary content
- All changes look the same in git log

**THE FIX:**
1. **Keep source code external** (scripts/ directory)
2. **Version control .py files** (reviewable)
3. **Update .hda from scripts** (documented process)
4. **Git commit .py changes first** (with message)
5. **Then commit .hda** (reference .py commit)

**COMMIT MESSAGE PATTERN:**
```
Update HDA PythonModule

Synced with scripts/hda_execute_workflow.py from commit abc1234
- Fixed input image reading
- Added better error handling
- See previous commit for code changes
```

**LESSON:** Treat .hda as build artifact. Keep source in .py files.

---

## Testing Gotchas

### 11. Unit Tests Pass, Integration Fails

**THE GOTCHA:**
```
$ python tests/run_tests.py
All tests passed! ✅

# Try in Houdini:
Error: Module 'comfy_bridge' not found ❌
```

**WHY IT HAPPENS:**
- Unit tests add module to sys.path manually
- Houdini uses different Python environment
- PYTHONPATH not configured in houdini.env
- Tests don't catch environment issues

**THE FIX:**
1. **Test in actual Houdini environment**
2. **Verify houdini.env settings**
3. **Add integration tests that run in Houdini**
4. **Document environment setup in tests/README**

**LESSON:** Unit tests are necessary but not sufficient. Always test in target environment.

---

## Error Messages That Lie

### 12. "Unknown command: icopoutput"

**WHAT IT SAYS:**
```
RuntimeError: icopoutput failed: Unknown command: icopoutput
```

**WHAT YOU THINK:**
"Typo? Missing module? Wrong context?"

**WHAT IT ACTUALLY MEANS:**
"This command was removed in Houdini 21. Your code is using a deprecated API that no longer exists."

**THE FIX:**
Search for "icopoutput" in HOUDINI_API_REFERENCE.md, find the workaround.

---

### 13. "AttributeError: 'CopNode' object has no attribute 'saveImage'"

**WHAT IT SAYS:**
```
AttributeError: 'CopNode' object has no attribute 'saveImage'
```

**WHAT YOU THINK:**
"Wrong node type? Need to cook first? Import missing?"

**WHAT IT ACTUALLY MEANS:**
"This method never existed. You're using an API from your imagination or bad documentation."

**THE FIX:**
Check HOUDINI_API_REFERENCE.md for what actually works.

---

## Prevention Checklist

Before committing code, verify:

- [ ] No hardcoded paths (search for `/home/`, `C:\`)
- [ ] All Houdini parameters use correct eval method
- [ ] All file paths expanded with `hou.text.expandString()`
- [ ] All workflow nodes type-checked before `.get()`
- [ ] Image color modes normalized (RGB)
- [ ] No deprecated hscript commands
- [ ] HDA updated if scripts changed
- [ ] Unit tests pass
- [ ] Integration test in Houdini passes
- [ ] Error messages user-friendly

**Golden Rule:** If it works only on your machine, it's not done.

---

## When in Doubt

1. Check HOUDINI_API_REFERENCE.md for verified methods
2. Check .claude/context.md for known issues
3. Add print() statements liberally
4. Test in clean Houdini session
5. Document new gotchas here for next time
