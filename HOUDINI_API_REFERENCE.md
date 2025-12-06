# Houdini 21 COP2 API Reference

## Verified Working Methods

### Parameter Evaluation
**CRITICAL: Use correct eval method for parameter type**
- String parameters: `parm.evalAsString()` ✅
- Int/Float parameters: `parm.eval()` ✅
- **NEVER** use `eval()` on string parameters - it treats them as Python expressions!

Example:
```python
# WRONG - will parse "127.0.0.1:8188" as Python code
server_address = node.parm('server_address').eval()  # ❌

# RIGHT - returns the string as-is
server_address = node.parm('server_address').evalAsString()  # ✅
```

### COP Node Resolution
- `cop_node.size()` → returns `(width, height)` tuple

### Reading Images from COP Nodes

**NO DIRECT PIXEL ACCESS AVAILABLE** - Must use workarounds

#### ✅ WORKING: File COP Source Reading
For File COP nodes, read the source file directly:
```python
if cop_node.type().name() == 'file':
    file_path_parm = cop_node.parm('filename1')  # ✅ Works
    if file_path_parm:
        file_path = file_path_parm.evalAsString()
        file_path = hou.text.expandString(file_path)  # ✅ Expands $HIP, $F, etc.

        if os.path.exists(file_path):
            # Read file directly with PIL/standard libs
            from PIL import Image
            image = Image.open(file_path)
```

**Use case:** When input is File COP, bypass COP rendering and read source directly

#### ❌ FAILED APPROACHES (Tried & Documented)

**Attempt 1: cop_node.saveImage()**
```python
cop_node.saveImage('/tmp/output.png')  # ❌ AttributeError: method doesn't exist
```
**Error:** `AttributeError: 'CopNode' object has no attribute 'saveImage'`

**Attempt 2: Create ROP Composite Node**
```python
rop = cop_node.createNode('rop_composite')  # ❌ Invalid context
```
**Error:** `hou.OperationFailed: Invalid node type name`
**Reason:** Can't create ROP nodes inside COP network context

**Attempt 3: hou.hscript("icopoutput")**
```python
hou.hscript(f"icopoutput -d {path} -f 1 1 {cop_node.path()}")  # ❌ Command removed
```
**Error:** `RuntimeError: icopoutput failed: Unknown command: icopoutput`
**Reason:** `icopoutput` command removed in Houdini 21

**Attempt 4: hou.hscript("mwrite")**
```python
hou.hscript(f"mwrite {cop_node.path()} {path}")  # ⚠️ Requires X11 display
```
**Status:** Works but requires X11 (fails in headless/server environments)

#### Recommended Approach
1. **For File COPs:** Read source file directly (fastest, most reliable) ✅
2. **For other COPs:** Ask user to save to file first, then read that file
3. **Production:** Document that only File COP inputs are supported

### Writing Images to COP Output

**NO DIRECT PIXEL WRITING AVAILABLE** - Must use File COP nodes

#### ✅ WORKING: Create/Update Internal File Node
```python
# Option 1: Create File node inside unlocked HDA
file_node = node.createNode('file', 'comfy_result')  # ✅ If HDA unlocked
file_node.parm('filename1').set(tmp_path)
file_node.cook()
```

**Limitation:** HDA must be unlocked (uncheck "Lock Contents" in Type Properties)

#### ✅ WORKING: Write to External File Path
```python
# Option 2: Save to external path (works with locked HDA)
output_dir = os.path.expanduser('~/comfyui_output')
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'output.png')

with open(output_path, 'wb') as f:
    f.write(png_data)

print(f"Output saved to: {output_path}")
```

**Use case:** When HDA is locked, save to known location and tell user where to find it

#### ✅ BEST PRACTICE: Output Path Parameter
```python
# Option 3: Let user specify output path (most flexible)
output_path = node.parm('output_path').evalAsString()
expanded = hou.text.expandString(output_path)  # Handles $HIP, $F, etc.

with open(expanded, 'wb') as f:
    f.write(png_data)
```

**Benefits:**
- Works with locked HDA
- User controls output location
- Supports frame sequences with $F4

## Methods That DON'T Exist or DON'T Work

### COP Node Methods
- ❌ `cop_node.saveImage()` - doesn't exist on COP nodes
- ❌ `cop_node.xRes()`, `yRes()`, `resolution()` - only on specific node types
- ❌ `cop_node.allPixelsAsString()` - doesn't work on input/File nodes
- ❌ `cop_node.allPixels()` - doesn't work on input/File nodes
- ❌ Direct pixel manipulation on input/output nodes

### Houdini 21 Removed Commands
- ❌ `hou.hscript("icopoutput")` - Command removed in Houdini 21
- ⚠️ `hou.hscript("mwrite")` - Exists but requires X11 display (fails headless)

### Node Creation Restrictions
- ❌ Can't create ROP nodes inside COP network context
- ❌ Can't create nodes inside locked HDA (must unlock first)

## Common Patterns & Best Practices

### Pattern: Safe Parameter Reading
```python
# Always check parameter exists before reading
parm = node.parm('parameter_name')
if parm:
    if parm.parmTemplate().type() == hou.parmTemplateType.String:
        value = parm.evalAsString()  # ✅ For strings
    else:
        value = parm.eval()  # ✅ For numbers
```

### Pattern: Path Expansion
```python
# Always expand Houdini variables in paths
raw_path = node.parm('file_path').evalAsString()
expanded_path = hou.text.expandString(raw_path)  # ✅ Expands $HIP, $F, $OS, etc.
```

### Pattern: Type Checking Workflow Data
```python
# Always check dict before calling .get()
for node_id, node_data in workflow.items():
    if isinstance(node_data, dict):  # ✅ Type check first
        class_type = node_data.get('class_type', '')
    else:
        print(f"Warning: Node {node_id} is not a dict")
        continue
```

### Pattern: Error-Resilient File I/O
```python
# Always handle file operations with try/except
try:
    with open(file_path, 'rb') as f:
        data = f.read()
except FileNotFoundError:
    hou.ui.displayMessage(f"File not found: {file_path}", severity=hou.severityType.Error)
except Exception as e:
    hou.ui.displayMessage(f"Error reading file: {e}", severity=hou.severityType.Error)
```

## Version Information

**Tested on:**
- Houdini 21.0 (Python 3.10)
- Ubuntu Linux (also tested on Windows/macOS via user reports)

**Known incompatibilities:**
- Houdini 19.x: `icopoutput` command still exists but deprecated
- Houdini 18.x and below: Not tested, likely different COP API

## Maintenance Protocol

**When adding new discoveries:**
1. Test the method/command thoroughly
2. Document exact error messages if it fails
3. Include working code examples with ✅
4. Add version information (Houdini X.X)
5. Update date at top of file

**Format:**
- ✅ = Verified working
- ❌ = Confirmed doesn't exist or doesn't work
- ⚠️ = Works with limitations/caveats

**Last Updated:** 2025-12-06
