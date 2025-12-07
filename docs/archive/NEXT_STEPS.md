# Next Steps - Execution Plan

**Last Updated:** 2025-12-07
**Current Phase:** Phase 1 - Critical Fixes
**Status:** Ready to begin

---

## Immediate Actionable Tasks (Next 1-2 Hours)

### BLOCKER: Task 1.1 - Update HDA with Latest Code

**Priority:** 🔴 CRITICAL - MUST DO FIRST
**Estimated Time:** 10 minutes
**Blocks:** Everything else
**Owner:** User (requires Houdini)

#### Steps to Execute

1. **Start Houdini**
   ```bash
   cd /path/to/your/project
   houdini your_scene.hip
   ```

2. **Locate ComfyUI Bridge node**
   - Navigate to `/img/cop2net1/` (or wherever you placed it)
   - Find the ComfyUI Bridge HDA node

3. **Open Type Properties**
   - Right-click the node
   - Select "Type Properties" from context menu
   - Type Properties dialog opens

4. **Navigate to PythonModule**
   - Click "Scripts" tab at top
   - Find "PythonModule" section in left panel
   - Current code (old) will be displayed

5. **Copy Latest Code**
   - Open external text editor
   - Open file: `/home/maxborg/houdini-comfy-bridge/scripts/hda_execute_workflow.py`
   - Select All (Ctrl+A)
   - Copy (Ctrl+C)

6. **Update HDA**
   - Back in Type Properties dialog
   - Select all text in PythonModule section (Ctrl+A)
   - Paste new code (Ctrl+V)
   - Click "Accept" button at bottom
   - Click "Apply" button

7. **Save HDA**
   - Right-click node again
   - Select "Save Node Type"
   - Confirm save to otls/comfyui_bridge.hda

8. **Verify Update**
   - In Houdini Python Shell:
   ```python
   node = hou.pwd()  # Or hou.node('/img/cop2net1/comfyui_bridge1')
   # Try to execute - should NOT see icopoutput error
   ```

#### How to Validate Success

✅ **Success Indicators:**
- No `icopoutput` errors in console
- No `AttributeError` for deprecated methods
- Console shows: "Reading directly from File COP source:" message
- Latest debug messages appear

❌ **Failure Indicators:**
- Still see "Unknown command: icopoutput"
- Console shows old debug messages
- Code hasn't updated

#### If Update Fails

**Problem:** Accept button doesn't save changes
**Solution:** Make sure to click both Accept AND Apply

**Problem:** Can't find Type Properties option
**Solution:** Right-click the NODE, not the network

**Problem:** Code reverts after closing dialog
**Solution:** Must click "Save Node Type" after accepting

---

### Task 1.2 - Test Input Image Upload

**Priority:** 🔴 CRITICAL
**Estimated Time:** 15-30 minutes
**Depends On:** Task 1.1 complete
**Owner:** User (requires Houdini + ComfyUI)

#### Prerequisites

- [ ] Task 1.1 complete (HDA updated)
- [ ] ComfyUI server running (localhost:8188)
- [ ] Test image available (512x512 PNG recommended)
- [ ] Test workflow with INPUT_ LoadImage node

#### Steps to Execute

1. **Start ComfyUI Server**
   ```bash
   cd /path/to/ComfyUI
   python main.py
   # Wait for "To see the GUI go to: http://127.0.0.1:8188"
   ```

2. **Verify Server Running**
   - Open browser: http://127.0.0.1:8188
   - Should see ComfyUI interface
   - Leave server running

3. **Create Test Scene in Houdini**
   - Create new COP network: `/img`
   - Inside network, create nodes:
     - File COP → Load test image
     - ComfyUI Bridge HDA

4. **Configure File COP**
   - Set "File Path" to test image
   - Example: `/home/maxborg/Pictures/test_512x512.png`
   - Verify image loads (should see preview)

5. **Configure ComfyUI Bridge**
   - Connect File COP output → Bridge input
   - Set parameters:
     - **Workflow File:** Point to workflow with INPUT_source_image node
     - **ComfyUI Host:** 127.0.0.1
     - **ComfyUI Port:** 8188

6. **Execute Workflow**
   - Click "Execute Workflow" button
   - Watch Houdini console for messages

7. **Monitor Output**
   ```
   Expected console messages:
   ✅ "Reading input image from: /img/cop2net1/file1"
   ✅ "Reading directly from File COP source: /path/to/test.png"
   ✅ "Read XXXX bytes from input COP"
   ✅ "Uploaded input image: {'name': 'houdini_input.png', ...}"
   ✅ "Setting LoadImage node 'source_image' to use: houdini_input.png"
   ✅ "Received 1 output image(s)"
   ```

#### How to Validate Success

✅ **Complete Success:**
- [ ] No errors in console
- [ ] All expected messages appear
- [ ] Output image generated
- [ ] Output image different from input (shows processing)

⚠️ **Partial Success:**
- [ ] Image uploads but workflow fails
- [ ] Workflow executes but wrong image used
- [ ] Output generated but can't display

❌ **Failure:**
- [ ] File COP reading fails
- [ ] Upload fails (network error)
- [ ] Workflow execution timeout
- [ ] ComfyUI server not responding

#### Debug Checklist

If upload fails:
- [ ] Verify File COP has valid source file
- [ ] Check file path exists: `os.path.exists(path)`
- [ ] Verify PIL available: `import PIL` in Houdini Python Shell
- [ ] Check ComfyUI input folder writable
- [ ] Try manual upload: `python dev/test_image_upload.py`

If workflow fails:
- [ ] Check ComfyUI console for errors
- [ ] Verify workflow JSON valid
- [ ] Check all model files available
- [ ] Verify INPUT_ node name matches parameter

---

### Task 1.3 - Fix Output Display

**Priority:** 🟡 HIGH
**Estimated Time:** 30 minutes
**Depends On:** Task 1.2 passing
**Owner:** User + Claude

#### Current Behavior
- Output saves to `~/comfyui_output/`
- User must manually load in File COP
- No automatic display

#### Recommended Solution: Add Output Path Parameter

**Steps:**

1. **Add Parameter to HDA**
   - Right-click node → Type Properties
   - Parameters tab
   - Add new parameter:
     - **Type:** String (File Reference)
     - **Name:** `output_path`
     - **Label:** "Output Path"
     - **Default:** `$HIP/comfy_output/output_$F4.png`
     - **File Type:** Any
     - **Tags:** `filechooser_mode: write`

2. **Update Code in PythonModule**
   - Locate `_write_png_to_cop()` function (line 292)
   - Replace fallback output directory logic:
   ```python
   # Get output path from parameter
   output_path = node.parm('output_path').evalAsString()
   expanded = hou.text.expandString(output_path)

   # Create directory if needed
   os.makedirs(os.path.dirname(expanded), exist_ok=True)

   # Write file
   with open(expanded, 'wb') as f:
       f.write(png_data)

   print(f"✅ Output saved: {expanded}")
   hou.ui.setStatusMessage(f"Output saved: {expanded}", severity=hou.severityType.Message)
   ```

3. **Test**
   - Execute workflow
   - Check console for "✅ Output saved: /path/to/output.png"
   - Verify file exists
   - Load in File COP to view

#### How to Validate Success

✅ **Success:**
- [ ] Parameter appears in UI
- [ ] Default path uses $HIP correctly
- [ ] Output directory created automatically
- [ ] File saved to specified path
- [ ] User can change output location
- [ ] Supports $F for frame sequences

---

### Task 1.4 - End-to-End Integration Test

**Priority:** 🔴 CRITICAL
**Estimated Time:** 1-2 hours
**Depends On:** Tasks 1.1, 1.2, 1.3 complete
**Owner:** User

#### Test Cases to Execute

**Test 1: Basic Image Processing**
```
Input: 512x512 test image (File COP)
Workflow: Simple img2img (denoise 0.5)
Expected: Modified image output
Validation: Output visually different from input
```

**Test 2: Parameter Control**
```
Input: Same image
Action: Change denoise strength via HDA parameter
Expected: Different output (more/less denoised)
Validation: Multiple executions produce different results
```

**Test 3: Error Handling**
```
Input: Invalid file path
Expected: Clear error message, no crash
Validation: Houdini doesn't crash, user sees helpful error
```

**Test 4: Multiple Outputs**
```
Workflow: Generate 3 variations (batch_size=3)
Expected: All 3 images saved
Validation: 3 files exist with correct naming
```

**Test 5: Frame Sequence**
```
Input: Change image per frame
Expected: Different output per frame
Validation: Frame 1, 10, 20 all have different outputs
```

#### Success Criteria

✅ **Phase 1 Complete When:**
- [ ] All 5 test cases pass
- [ ] No crashes or hangs
- [ ] Error messages clear and helpful
- [ ] Performance acceptable (< 30s per image)
- [ ] User can work with system without assistance

---

## Short-Term Goals (This Week)

### Phase 2: Code Quality Improvements

#### Task 2.1: Clean Repository
**Time:** 15 minutes
```bash
# Delete backup HDAs
rm -rf /home/maxborg/houdini-comfy-bridge/otls/backup/

# Update .gitignore
echo "otls/backup/" >> .gitignore

# Verify cleanup
du -sh otls/
git status
```

#### Task 2.2: Fix Hardcoded Paths
**Time:** 20 minutes

**Files to update:**
- `dev/test_image_upload.py:5`
- `dev/test_retrieve_image.py:5`

**Pattern to replace:**
```python
# OLD
sys.path.insert(0, '/home/maxborg/houdini-comfy-bridge/python')

# NEW
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
```

#### Task 2.3: Create Houdini Package File
**Time:** 30 minutes

Create: `packages/comfy_bridge.json`
```json
{
    "env": [
        {"COMFY_BRIDGE_ROOT": "$HOUDINI_PACKAGE_PATH/comfy_bridge"},
        {"PYTHONPATH": {"value": "$COMFY_BRIDGE_ROOT/python", "method": "prepend"}},
        {"HOUDINI_OTLSCAN_PATH": {"value": "$COMFY_BRIDGE_ROOT/otls", "method": "prepend"}}
    ],
    "version": "0.1.0",
    "description": "ComfyUI integration for Houdini COP networks"
}
```

**Test:** Clean Houdini install, verify HDA loads via package

---

## Testing Approach

### Before Each Code Change

1. ✅ Run unit tests: `python tests/run_tests.py`
2. ✅ Verify no hardcoded paths: `grep -r "/home/maxborg" .`
3. ✅ Check GOTCHAS.md for relevant pitfalls
4. ✅ Update HDA if scripts changed

### After Each Code Change

1. ✅ Test in Houdini (integration test)
2. ✅ Verify all test cases still pass
3. ✅ Update CHANGELOG.md
4. ✅ Update context.md if state changes
5. ✅ Commit with clear message

### Before Committing

1. ✅ All tests pass
2. ✅ No console errors
3. ✅ Documentation updated
4. ✅ CHANGELOG.md updated
5. ✅ No hardcoded paths
6. ✅ HDA matches scripts

---

## How to Use This Document

**When starting work:**
1. Read "Immediate Actionable Tasks" section
2. Identify current blocking task
3. Execute steps in order
4. Validate success before moving on

**When task complete:**
1. Check off validation items
2. Update `.claude/context.md` with progress
3. Update `CHANGELOG.md` with attempt
4. Move to next task

**When stuck:**
1. Check "Debug Checklist" for current task
2. Review GOTCHAS.md for similar issues
3. Check HOUDINI_API_REFERENCE.md for API help
4. Ask for guidance with specific error message

**When interrupted:**
1. Note current task in context.md
2. Note any blockers discovered
3. Update this file with progress
4. Easy to resume later

---

## Progress Tracking

### Phase 1 Status (0% Complete)

- [ ] Task 1.1: Update HDA with latest code
- [ ] Task 1.2: Test input image upload
- [ ] Task 1.3: Fix output display
- [ ] Task 1.4: End-to-end integration test

**Estimated Time Remaining:** 4 hours
**Blockers:** Task 1.1 (user must do in Houdini)

### Phase 2 Status (Not Started)

- [ ] Task 2.1: Clean repository
- [ ] Task 2.2: Fix hardcoded paths
- [ ] Task 2.3: Create package file

**Estimated Time:** 2 hours
**Blockers:** Phase 1 must complete first

---

## Quick Command Reference

**Run tests:**
```bash
cd /home/maxborg/houdini-comfy-bridge
python tests/run_tests.py
```

**Start ComfyUI:**
```bash
cd /path/to/ComfyUI
python main.py
```

**Check for hardcoded paths:**
```bash
cd /home/maxborg/houdini-comfy-bridge
grep -r "/home/maxborg" --exclude-dir=.git --exclude="*.md" .
```

**View recent changes:**
```bash
git log --oneline -10
git diff HEAD~1
```

**Update documentation:**
```bash
# After making changes:
nano .claude/context.md    # Update current state
nano CHANGELOG.md          # Record what was attempted
nano NEXT_STEPS.md         # Update progress
```

---

**Remember:** Read `.claude/context.md` first, work sequentially through tasks, validate each step, update documentation as you go!
