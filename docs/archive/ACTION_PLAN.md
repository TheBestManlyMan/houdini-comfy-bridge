# Action Plan - Houdini-ComfyUI Bridge

**Last Updated:** 2025-12-06
**Status:** In Progress
**Next Review:** After Phase 1 completion

---

## Overview

This document tracks the step-by-step action plan for fixing issues and improving the Houdini-ComfyUI Bridge. Tasks are organized by priority and phase.

**Legend:**
- 🔴 Critical - Blocking core functionality
- 🟡 High - Important for usability
- 🟢 Medium - Quality of life improvements
- 🔵 Low - Nice to have

**Status:**
- ⏳ Pending
- 🚧 In Progress
- ✅ Done
- ❌ Blocked
- ⏸️ Paused

---

## Phase 1: Critical Path - Get It Working

**Goal:** Fix blocking issues preventing basic functionality
**Target:** Complete within 1 day (4 hours total)

### Task 1.1: Update HDA with Latest Code 🔴 Critical
**Status:** ⏳ Pending
**Priority:** Highest - All other fixes depend on this
**Time:** 10 minutes

**Problem:**
- HDA PythonModule still contains old code with `icopoutput` bug
- Latest fixes in `scripts/hda_execute_workflow.py` not being used
- User error logs show old code executing

**Solution:**
```
1. Open Houdini
2. Find ComfyUI Bridge node in network
3. Right-click → Type Properties
4. Navigate to: Scripts tab → PythonModule section
5. Open: scripts/hda_execute_workflow.py in text editor
6. Copy entire file contents
7. Paste into PythonModule section (replace all)
8. Click: Accept button
9. Click: Apply button
10. Save HDA file
```

**Verification:**
```python
# In Houdini Python Shell, verify update:
node = hou.node('/img/cop2net1/comfyui_bridge1')
# Run workflow and check console for:
# "Reading directly from File COP source:" (NEW code)
# NOT "icopoutput" error (OLD code)
```

**Success Criteria:**
- ✅ No `icopoutput` errors in console
- ✅ Input image reading code executes
- ✅ Latest debug messages appear

**Dependencies:** None
**Blocks:** Tasks 1.2, 1.3, 1.4

---

### Task 1.2: Test Input Image Upload 🔴 Critical
**Status:** ⏳ Pending (blocked by 1.1)
**Priority:** Critical
**Time:** 15 minutes

**Problem:**
- Input images not being uploaded to ComfyUI
- Workflow uses cached/default images instead
- Image I/O never tested end-to-end

**Solution:**
```
Test Procedure:
1. In Houdini COP network:
   - Create File COP node
   - Load test image: /path/to/test_image.png
   - Connect File COP → ComfyUI Bridge input

2. Configure ComfyUI Bridge:
   - workflow_path: Point to test workflow with LoadImage INPUT node
   - server_address: 127.0.0.1:8188

3. Execute workflow (click Execute button)

4. Monitor console output for:
   ✓ "Reading directly from File COP source: /path/to/test_image.png"
   ✓ "Read XXXX bytes from input COP"
   ✓ "Uploaded input image: {'name': 'houdini_input.png', ...}"
   ✓ "Setting LoadImage node 'source_image' to use: houdini_input.png"
   ✓ "Received 1 output image(s)"
```

**Debug Checklist if Fails:**
- [ ] Check File COP has valid source file
- [ ] Verify file path exists: `os.path.exists(path)`
- [ ] Check PIL/Pillow available: `import PIL`
- [ ] Verify ComfyUI input folder writable
- [ ] Test API upload directly: `dev/test_image_upload.py`

**Success Criteria:**
- ✅ File COP source image read successfully
- ✅ Image uploaded to ComfyUI `/input/` folder
- ✅ Workflow receives uploaded image (not cached)
- ✅ New output generated (different from previous)

**Dependencies:** 1.1
**Blocks:** 1.4

---

### Task 1.3: Fix Output Display 🟡 High
**Status:** ⏳ Pending (blocked by 1.1)
**Priority:** High - User can't see results
**Time:** 30 minutes

**Problem:**
- HDA is locked → can't create internal File node
- Outputs save to `~/comfyui_output/` directory
- User must manually load results in separate File COP
- No visual feedback in Houdini

**Solution Options:**

#### Option A: Unlock HDA (Quick Fix)
```
Time: 5 minutes
Steps:
1. Right-click HDA → Type Properties
2. Basic tab
3. Uncheck "Lock Contents"
4. Apply
5. Test: Code should create internal File node successfully
```
**Pros:** Works immediately
**Cons:** HDA internals exposed, less professional

#### Option B: Add Output Path Parameter (Recommended)
```
Time: 30 minutes
Steps:
1. Edit HDA parameters (Type Properties → Parameters tab)
2. Add new parameter:
   - Name: output_path
   - Label: Output Path
   - Type: String (File Reference)
   - Default: $HIP/comfy_output/output_$F4.png
3. Update _write_png_to_cop() in PythonModule:
   ```python
   output_path = node.parm('output_path').evalAsString()
   expanded = hou.text.expandString(output_path)
   os.makedirs(os.path.dirname(expanded), exist_ok=True)
   with open(expanded, 'wb') as f:
       f.write(png_data)
   print(f"✅ Output saved: {expanded}")
   ```
4. Test and verify
```
**Pros:** User controls output, works with locked HDA, supports frame sequences
**Cons:** Takes longer to implement

**Recommendation:** Implement Option B for production quality

**Verification:**
```
1. Execute workflow
2. Check console: "✅ Output saved: /path/to/output.png"
3. Verify file exists: ls $HIP/comfy_output/
4. Load in File COP to view result
```

**Success Criteria:**
- ✅ Output path configurable via parameter
- ✅ Supports Houdini variables ($HIP, $F, $OS)
- ✅ Creates output directory if missing
- ✅ Clear message shows output location

**Dependencies:** 1.1
**Blocks:** 1.4

---

### Task 1.4: End-to-End Integration Test 🔴 Critical
**Status:** ⏳ Pending (blocked by 1.1, 1.2, 1.3)
**Priority:** Critical - Validates entire pipeline
**Time:** 1-2 hours

**Goal:** Test complete workflow from Houdini input to output

**Test Procedure:**
```
Setup:
1. Start ComfyUI: python main.py
2. Verify ComfyUI at http://127.0.0.1:8188
3. Prepare test workflow with:
   - INPUT_source_image (LoadImage)
   - Processing nodes (VAEEncode, KSampler, etc.)
   - SaveImage output

Test Cases:

Test 1: Basic Image Processing
- Input: 512x512 test image
- Workflow: Simple img2img (denoise 0.5)
- Expected: Modified image output

Test 2: Parameter Control
- Input: Same image
- Modify: Change denoise strength via HDA parameter
- Expected: Different output (more/less denoised)

Test 3: Error Handling
- Input: Invalid file path
- Expected: Clear error message, no crash

Test 4: Multiple Outputs
- Workflow: Generate 3 variations
- Expected: All 3 images saved with incrementing names

Test 5: Frame Sequence
- Input: Sequence of images (frame 1-10)
- Expected: Batch processing, output sequence
```

**Success Criteria:**
- ✅ All test cases pass
- ✅ No crashes or hangs
- ✅ Clear error messages for failures
- ✅ Performance acceptable (< 30s per image)

**Dependencies:** 1.1, 1.2, 1.3
**Blocks:** Phase 2

---

## Phase 2: Code Quality - Cleanup & Optimization

**Goal:** Remove redundant code, fix technical debt
**Target:** Complete within 1 day (2 hours total)
**Prerequisites:** Phase 1 complete and tested

### Task 2.1: Remove Unused Files 🗑️ 🟢 Medium
**Status:** ⏳ Pending
**Time:** 10 minutes

**Files to Delete:**
```bash
# Backup HDAs (38 files, ~180KB)
rm -rf otls/backup/

# Unused reference implementation
rm scripts/comfy_cop_node.py

# Empty directory
rmdir houdini/otls/

# Temporary debug files
rm /tmp/workflow_debug.json
rm /tmp/comfyui_payload_debug.json
```

**Update .gitignore:**
```bash
cat >> .gitignore << 'EOF'

# HDA backups (Houdini creates these)
otls/backup/

# Debug output
/tmp/
*.log

# Development test files
dev/
EOF
```

**Verification:**
```bash
# Verify git status clean
git status

# Check reduced size
du -sh otls/
```

**Success Criteria:**
- ✅ 38 backup files deleted
- ✅ 180KB+ space freed
- ✅ Unused code removed
- ✅ .gitignore updated

---

### Task 2.2: Move Test Files to dev/ 🟢 Medium
**Status:** ⏳ Pending
**Time:** 15 minutes

**Reorganize:**
```bash
# Create dev directory
mkdir -p dev/

# Move test scripts
mv ~/test_image_upload.py dev/
mv ~/test_retrieve_image.py dev/

# Update import paths in moved files
sed -i "s|sys.path.insert(0, '/home/maxborg/houdini-comfy-bridge/python')|sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))|" dev/test_*.py
```

**Update files:**
- [x] Fix import paths to use relative paths
- [x] Add dev/README.md explaining test scripts
- [x] Update main README to reference dev/ folder

**Success Criteria:**
- ✅ All test scripts in dev/
- ✅ Import paths use relative references
- ✅ Scripts still work after move

---

### Task 2.3: Fix Hardcoded Paths 🟡 High
**Status:** ⏳ Pending
**Time:** 20 minutes

**Files to Update:**
1. `scripts/hda_execute_workflow.py:12`
2. `dev/test_image_upload.py:5` (after move)
3. `dev/test_retrieve_image.py:5` (after move)

**Replace Pattern:**
```python
# OLD - Hardcoded
bridge_path = '/home/maxborg/houdini-comfy-bridge/python'

# NEW - Relative
import os
bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
if bridge_path not in sys.path:
    sys.path.insert(0, bridge_path)
```

**Or Better (for HDA):**
```python
# Trust PYTHONPATH from houdini.env, fallback to relative
try:
    from comfy_bridge import ComfyAPI, ComfyWorkflowParser
except ImportError:
    # Development fallback
    import sys, os
    bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
    sys.path.insert(0, bridge_path)
    from comfy_bridge import ComfyAPI, ComfyWorkflowParser
```

**Success Criteria:**
- ✅ No hardcoded paths remain
- ✅ Code works from any installation directory
- ✅ Works with PYTHONPATH or without

---

### Task 2.4: Create Houdini Package File 🟡 High
**Status:** ⏳ Pending
**Time:** 30 minutes

**Create:** `packages/comfy_bridge.json`

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
    ],
    "version": "0.1.0",
    "description": "ComfyUI integration for Houdini COP networks"
}
```

**Installation Instructions:**
```markdown
# Add to README.md

## Installation (Package Method - Recommended)

1. Copy repository to: `/path/to/houdini-comfy-bridge`
2. Copy package file to Houdini packages:
   ```bash
   cp packages/comfy_bridge.json ~/houdini21.0/packages/
   ```
3. Edit package file, update COMFY_BRIDGE_ROOT to your installation path
4. Restart Houdini
5. Test: Tab → "comfy" → ComfyUI Bridge should appear
```

**Success Criteria:**
- ✅ Package file created
- ✅ Installation tested on clean Houdini
- ✅ README updated with package method
- ✅ No manual houdini.env editing needed

---

## Phase 3: Documentation & Polish

**Goal:** Update docs, add tests, prepare for release
**Target:** Complete within 2 days (3 hours total)
**Prerequisites:** Phase 1 & 2 complete

### Task 3.1: Update README.md 🔵 Low
**Status:** ⏳ Pending
**Time:** 30 minutes

**Sections to Update:**

1. **Roadmap** - Mark completed items:
   - [x] Input image support (COP → ComfyUI)  ✅ DONE
   - [x] Output image retrieval  ✅ DONE
   - [ ] Batch processing interface
   - [ ] WebSocket support

2. **Installation** - Add package method first (recommended)

3. **Troubleshooting** - Add new section:
   ```markdown
   ### "HDA not updating after editing script"
   The HDA caches Python code internally. After editing
   scripts/hda_execute_workflow.py, you must update the HDA:
   1. Right-click node → Type Properties
   2. Scripts → PythonModule
   3. Copy updated script content
   4. Accept → Apply
   ```

4. **Usage** - Update with actual working features

---

### Task 3.2: Create SETUP.md 🔵 Low
**Status:** ⏳ Pending
**Time:** 30 minutes

**New File:** `SETUP.md`

**Content Outline:**
```markdown
# Setup Guide

## Installation Methods

### Method 1: Houdini Package (Recommended)
[Package installation steps]

### Method 2: Manual houdini.env
[Current README instructions]

## Configuration

### ComfyUI Server
[How to start ComfyUI, default ports, etc.]

### Workflow Setup
[How to create INPUT nodes in ComfyUI]

## Development Setup

### For Contributors
[Git clone, development workflow]

### Updating HDA Code
[How to sync script changes to HDA]

### Running Tests
[How to run test suite]

## Troubleshooting
[Common issues and solutions]
```

---

### Task 3.3: Update HOUDINI_API_REFERENCE.md ✅ Done
**Status:** ✅ Complete
**Time:** 15 minutes (completed)

**Updates Applied:**
- ✅ Added File COP reading method (working)
- ✅ Documented all failed approaches
- ✅ Added output writing methods
- ✅ Added common patterns section
- ✅ Added version information
- ✅ Updated maintenance protocol

---

### Task 3.4: Add Integration Tests 🟢 Medium
**Status:** ⏳ Pending
**Time:** 2 hours

**Create:** `tests/test_integration.py`

**Test Coverage:**
```python
class TestHDAIntegration(unittest.TestCase):
    """Integration tests for HDA workflow execution"""

    def test_file_cop_reading(self):
        """Test reading image from File COP node"""
        # Setup File COP with test image
        # Read via _read_cop_image_as_png()
        # Verify correct bytes returned

    def test_image_upload(self):
        """Test uploading image to ComfyUI"""
        # Upload test image
        # Verify appears in ComfyUI /input/ folder

    def test_workflow_execution(self):
        """Test full workflow execution"""
        # Load test workflow
        # Execute with input image
        # Verify output generated

    def test_parameter_mapping(self):
        """Test INPUT node parameter mapping"""
        # Workflow with INPUT nodes
        # Set parameters in HDA
        # Verify workflow updated correctly

    def test_error_handling(self):
        """Test error cases gracefully handled"""
        # Invalid file path
        # Server unavailable
        # Malformed workflow
```

**Success Criteria:**
- ✅ All integration tests pass
- ✅ Coverage > 80% for main execution path
- ✅ Tests run in CI/CD (if applicable)

---

## Progress Tracking

### Completion Status

**Phase 1: Critical Path**
- [ ] 1.1 Update HDA (0%)
- [ ] 1.2 Test Input Upload (0%)
- [ ] 1.3 Fix Output Display (0%)
- [ ] 1.4 Integration Test (0%)

**Overall:** 0/4 tasks complete (0%)

**Phase 2: Code Quality**
- [ ] 2.1 Remove Unused Files (0%)
- [ ] 2.2 Move Test Files (0%)
- [ ] 2.3 Fix Hardcoded Paths (0%)
- [ ] 2.4 Create Package File (0%)

**Overall:** 0/4 tasks complete (0%)

**Phase 3: Documentation**
- [ ] 3.1 Update README (0%)
- [ ] 3.2 Create SETUP.md (0%)
- [x] 3.3 Update API Reference (100%) ✅
- [ ] 3.4 Add Integration Tests (0%)

**Overall:** 1/4 tasks complete (25%)

---

## Timeline

| Phase | Tasks | Est. Time | Target Date | Status |
|-------|-------|-----------|-------------|--------|
| Phase 1 | 4 | 4 hours | Day 1 | ⏳ Pending |
| Phase 2 | 4 | 2 hours | Day 2 | ⏳ Pending |
| Phase 3 | 4 | 3 hours | Day 3-4 | 🚧 Started (1/4) |

**Total Estimated Time:** 9 hours
**Expected Completion:** 4 days

---

## Notes & Decisions

### 2025-12-06
- Created ACTION_PLAN.md to track progress
- Updated HOUDINI_API_REFERENCE.md with latest API discoveries
- Identified critical blocker: HDA code not updated
- Recommendation: Prioritize Task 1.1 immediately

### Decision Log

**Output Display Method:** Chose Option B (output path parameter)
- Reason: More flexible, works with locked HDA, professional UX
- Alternative considered: Unlocking HDA (too permissive)

**Code Structure:** Keep procedural style for now
- Reason: Already working, simpler to maintain
- Future: Consider OOP refactor after stabilization

---

## Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| HDA update breaks existing users | High | Low | Git tag before changes, provide rollback |
| Hardcoded paths break on other machines | High | High | Task 2.3 addresses this |
| Integration tests take too long | Medium | Medium | Mock ComfyUI server for tests |
| Package file not found by Houdini | High | Low | Document installation clearly |

---

**End of Action Plan**
