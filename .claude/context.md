# Project Context - Current State

**Last Updated:** 2025-12-07
**Current Phase:** Phase 1 - Critical Fixes (0% complete)
**Project Status:** 🔴 NON-FUNCTIONAL - Requires immediate fixes

---

## Executive Summary

The Houdini-ComfyUI Bridge is currently **not working** in production. While core Python modules are functional and tested, the HDA (Houdini Digital Asset) contains outdated code with deprecated commands. The latest fixes exist in external scripts but have NOT been loaded into the HDA yet.

**Critical Blocker:** HDA PythonModule contains old code - MUST be updated before any testing can proceed.

---

## Current Phase: Phase 1 - Critical Fixes

**Goal:** Get basic workflow execution working end-to-end
**Target:** Complete within 4 hours
**Progress:** 0/4 tasks complete

### Active Tasks

#### Task 1.1: Update HDA with Latest Code [BLOCKING]
- **Status:** ⏳ Pending
- **Priority:** 🔴 CRITICAL - Everything blocked until this is done
- **Issue:** HDA still has old `icopoutput` code despite script updates
- **Evidence:** User error logs show deprecated commands executing
- **Action Required:**
  1. Open Houdini
  2. Right-click node → Type Properties
  3. Scripts → PythonModule
  4. Copy scripts/hda_execute_workflow.py content
  5. Paste into PythonModule (replace all)
  6. Accept → Apply → Save

**NOTHING ELSE CAN BE TESTED UNTIL THIS IS DONE**

#### Task 1.2: Test Input Image Upload
- **Status:** ⏳ Pending (blocked by 1.1)
- **Priority:** 🔴 CRITICAL
- **Code Status:** Latest code exists but untested
- **What works:** File COP source reading (in scripts/hda_execute_workflow.py:234-255)
- **What's unknown:** Does it work in practice? Need real test.

#### Task 1.3: Fix Output Display
- **Status:** ⏳ Pending (blocked by 1.1)
- **Priority:** 🟡 HIGH
- **Current Behavior:** Saves to ~/comfyui_output/ (works but clunky)
- **Issue:** HDA locked, can't create internal File nodes
- **Recommended Fix:** Add output_path parameter for user control

#### Task 1.4: End-to-End Integration Test
- **Status:** ⏳ Pending (blocked by 1.1, 1.2, 1.3)
- **Priority:** 🔴 CRITICAL
- **Purpose:** Validate entire pipeline works

---

## What's Working ✅

### Core Python Modules (100% Functional)

**comfy_api.py (289 lines):**
- ✅ Server connection checks (`is_server_alive()`)
- ✅ Image upload (`upload_image()`)
- ✅ Workflow queueing (`queue_prompt()`)
- ✅ Execution monitoring (`wait_for_completion()`)
- ✅ Image download (`get_image()`)
- ✅ Full workflow execution (`execute_workflow()`)
- **Test Status:** Unit tests passing

**comfy_parser.py (503 lines):**
- ✅ Workflow JSON loading (`load_workflow()`)
- ✅ Format conversion (frontend → API)
- ✅ INPUT_ node detection (`_extract_input_nodes()`)
- ✅ Parameter generation (`get_input_parameters()`)
- ✅ Workflow value updates (`update_workflow_inputs()`)
- ✅ Type checking and validation
- **Test Status:** Unit tests passing

### Development Tools

- ✅ Unit test suite (tests/ directory)
- ✅ Debug scripts (dev/ directory)
- ✅ HDA builder (scripts/build_hda.py)
- ✅ Comprehensive documentation (README, QUICKSTART, etc.)

---

## What's Broken ❌

### Production HDA (otls/comfyui_bridge.hda)

**Critical Issues:**

1. **Outdated PythonModule Code** 🔴
   - Still contains old `icopoutput` command
   - Latest fixes NOT loaded
   - User sees errors from deprecated code
   - **Impact:** HDA completely non-functional

2. **Input Image Reading** ⚠️
   - Code exists (scripts/hda_execute_workflow.py:214-289)
   - Uses direct File COP source reading (✅ Good approach)
   - **NOT TESTED** - Unknown if it works
   - **Impact:** Cannot process input images

3. **Output Display** ⚠️
   - Works but saves to ~/comfyui_output/
   - User must manually load in separate File COP
   - No visual feedback in HDA
   - **Impact:** Poor user experience

### Code Quality Issues

4. **Hardcoded Paths** 🟡
   - scripts/hda_execute_workflow.py:13 (now fixed to relative)
   - dev/test_*.py files still have hardcoded paths
   - **Impact:** Won't work on other machines

5. **Repository Clutter** 🟢
   - 38 backup HDAs in otls/backup/ (~180KB)
   - Unnecessary git history bloat
   - **Impact:** Confusion, wasted space

---

## Active Blockers

### Blocker #1: HDA Code Not Updated
- **Severity:** 🔴 CRITICAL
- **What:** Production HDA has old code
- **Why it matters:** ALL recent fixes ineffective
- **Blocked tasks:** 1.2, 1.3, 1.4 (everything)
- **Resolution:** Manual HDA update (10 minutes)
- **Owner:** User must do this in Houdini

### Blocker #2: No End-to-End Test
- **Severity:** 🔴 CRITICAL
- **What:** Never tested File COP → ComfyUI → Output
- **Why it matters:** Don't know if it actually works
- **Blocked by:** Blocker #1
- **Resolution:** After HDA update, run integration test
- **Estimated time:** 15-30 minutes

---

## Recent Changes (Dec 6, 2025)

### Completed
- ✅ Updated HOUDINI_API_REFERENCE.md with working methods
- ✅ Fixed scripts/hda_execute_workflow.py with File COP reading
- ✅ Added type checking to prevent 'str' has no attribute 'get' errors
- ✅ Created ACTION_PLAN.md with phased approach
- ✅ Created REPOSITORY_AUDIT.md with full analysis

### Attempted (Failed)
- ❌ Reading COP pixels via cop_node.saveImage() - doesn't exist
- ❌ Using hou.hscript("icopoutput") - removed in Houdini 21
- ❌ Creating ROP nodes in COP context - invalid context
- ❌ Using mwrite command - requires X11 display

### Pending
- ⏳ Update HDA PythonModule with latest code
- ⏳ Test input image upload
- ⏳ Test output retrieval
- ⏳ Add output_path parameter to HDA

---

## Known Issues & Workarounds

### Issue: HDA Development Workflow
**Problem:** Editing scripts/ files doesn't update HDA
**Root Cause:** HDA caches PythonModule in .hda file
**Workaround:** Manually copy/paste code into Type Properties
**Long-term Fix:** Use external script reference during development

### Issue: Can't Read Non-File COP Nodes
**Problem:** Only File COPs supported for input
**Root Cause:** Houdini 21 removed icopoutput command
**Workaround:** User must use File COP as input
**Long-term Fix:** Implement mwrite workaround (requires X11)

### Issue: Output Not Displayed in Houdini
**Problem:** Images save to ~/comfyui_output/ instead of HDA
**Root Cause:** Locked HDA can't create internal File nodes
**Workaround:** User loads output manually in File COP
**Long-term Fix:** Add output_path parameter (Phase 1 Task 1.3)

---

## Environment & Dependencies

### Working Environment
- **OS:** Ubuntu Linux (Houdini 21.0)
- **Python:** 3.10 (Houdini's Python)
- **Houdini:** 21.0
- **ComfyUI:** Latest (API format compatible)

### Required Dependencies
- **Standard Library Only:**
  - json, urllib, io, uuid, time, os, sys
  - PIL/Pillow (for image processing)
- **No external packages required** (except PIL)

### Optional Dependencies
- PIL/Pillow (included in most Houdini distributions)
- If missing: Install via Houdini Python's pip

---

## Testing Status

### Unit Tests
- ✅ test_api.py - All passing
- ✅ test_parser.py - All passing
- ✅ Core functionality validated

### Integration Tests
- ❌ HDA execution - NOT TESTED (blocked by outdated HDA)
- ❌ File COP reading - NOT TESTED
- ❌ Image upload - NOT TESTED
- ❌ Output retrieval - NOT TESTED
- ❌ End-to-end workflow - NOT TESTED

**Test Coverage:** ~40% (only unit tests, no integration)

---

## Next Immediate Priorities

### This Session (Next 1-2 hours)

1. **USER ACTION REQUIRED:** Update HDA PythonModule
   - Cannot proceed without this
   - 10 minute task
   - Must be done in Houdini

2. **After HDA update:**
   - Start ComfyUI server
   - Create test scene in Houdini
   - Load File COP with test image
   - Execute workflow
   - Verify: input upload, execution, output retrieval

3. **If tests pass:**
   - Add output_path parameter to HDA
   - Test frame sequences
   - Document working configuration

### This Week

- Complete Phase 1 (all 4 tasks)
- Begin Phase 2 (code cleanup)
- Remove hardcoded paths
- Clean up 38 backup HDAs

---

## Communication Notes

**When user asks to work on this project, ALWAYS:**
1. Read this file first (.claude/context.md)
2. Check NEXT_STEPS.md for execution plan
3. Verify current blockers haven't changed
4. Update this file with any progress
5. Alert user to any conflicts

**When making changes:**
- Update CHANGELOG.md with attempts
- Update this file with new findings
- Keep ACTION_PLAN.md in sync with progress

**When discovering new issues:**
- Add to "Known Issues & Workarounds" section
- Update GOTCHAS.md with lessons learned
- Add to HOUDINI_API_REFERENCE.md if API-related

---

## Quick Reference

**Project Root:** `/home/maxborg/houdini-comfy-bridge/`

**Key Files:**
- Production HDA: `otls/comfyui_bridge.hda` (OUTDATED)
- Latest script: `scripts/hda_execute_workflow.py` (CURRENT)
- Core modules: `python/comfy_bridge/` (WORKING)

**Debug Locations:**
- Workflow debug: `/tmp/workflow_debug.json`
- API payload: `/tmp/comfyui_payload_debug.json`
- Output images: `~/comfyui_output/`

**Status Indicators:**
- 🔴 Critical / Blocking
- 🟡 High Priority
- 🟢 Medium Priority
- 🔵 Low Priority
- ✅ Working / Complete
- ❌ Broken / Failed
- ⚠️ Partial / Needs Testing
- ⏳ Pending / Not Started

---

**Last Status Check:** 2025-12-07 - HDA code refactored, paths fixed, ready for testing

---

## Current Code State

### What Just Changed ✅

**HDA/PythonModule.py:**
- ✅ Dynamic path resolution (no hardcoded paths)
- ✅ Checks COMFY_BRIDGE_ROOT env var
- ✅ Searches PYTHONPATH intelligently
- ✅ Falls back gracefully with warnings

**HDA/hda_interface.py:**
- ✅ Dynamic scripts directory finding
- ✅ Fixed hou.text.expandString() calls (was using wrong API)
- ✅ Better error messages
- ✅ Works from any installation location

**scripts/hda_execute_workflow.py:**
- ✅ Supports both old and new parameter structures
- ✅ Multiple input image support (up to 10)
- ✅ Intelligent input mapping from node.userData()
- ✅ Unique filenames per input (houdini_input_0.png, etc.)
- ✅ Fixed string parameter evaluation

### What Needs Testing ⚠️

**Not yet tested:**
1. HDA PythonModule needs to be updated with new code
2. End-to-end workflow execution
3. Multiple input image upload
4. Path resolution on different machines

**Next Step:** Copy HDA/PythonModule.py content into HDA PythonModule section
