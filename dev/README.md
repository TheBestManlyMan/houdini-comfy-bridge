# Development & Test Scripts

This directory contains development and testing scripts for the Houdini-ComfyUI Bridge.

## Scripts

### test_image_upload.py
Tests the image upload and download functionality with ComfyUI.

**Usage:**
```bash
# Make sure ComfyUI is running first
python dev/test_image_upload.py
```

**What it does:**
1. Connects to ComfyUI at 127.0.0.1:8188
2. Creates a 100x100 red test image
3. Uploads it to ComfyUI's input folder
4. Downloads it back and verifies integrity

**Expected output:**
```
✅ Connected to ComfyUI server
✅ Upload successful!
✅ Retrieved 1234 bytes
✅ All tests passed!
```

---

### test_retrieve_image.py
Tests retrieving images from ComfyUI execution history.

**Usage:**
```bash
python dev/test_retrieve_image.py
```

**What it does:**
1. Queries ComfyUI history for a specific prompt ID
2. Extracts output image information
3. Downloads the generated images

**Note:** You'll need to update the `prompt_id` variable with a valid prompt ID from a recent ComfyUI execution.

---

## Requirements

- ComfyUI server running at http://127.0.0.1:8188
- Python 3.9+
- PIL/Pillow (for image operations)

## Development Notes

These scripts use relative imports to find the `comfy_bridge` module, so they can be run from any location as long as the repository structure is maintained.
