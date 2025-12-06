#!/usr/bin/env python3
"""Test uploading an image to ComfyUI and verifying it's available"""

import sys
import os

# Add parent directory's python module to path (relative to this script)
bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
bridge_path = os.path.abspath(bridge_path)
sys.path.insert(0, bridge_path)

from comfy_bridge import ComfyAPI
from PIL import Image
import io

# Connect to ComfyUI
api = ComfyAPI(host='127.0.0.1', port=8188)

print("=" * 60)
print("Testing ComfyUI Image Upload")
print("=" * 60)

# Check server is alive
if not api.is_server_alive():
    print("❌ ERROR: Cannot connect to ComfyUI at 127.0.0.1:8188")
    print("   Make sure ComfyUI is running!")
    sys.exit(1)

print("✅ Connected to ComfyUI server")

# Create a simple test image (100x100 red square)
test_image = Image.new('RGB', (100, 100), color='red')
png_buffer = io.BytesIO()
test_image.save(png_buffer, format='PNG')
png_data = png_buffer.getvalue()

print(f"\n📤 Uploading test image ({len(png_data)} bytes)...")

# Upload the image
try:
    result = api.upload_image(
        png_data,
        filename='test_upload.png',
        image_type='input',
        overwrite=True
    )
    print(f"✅ Upload successful!")
    print(f"   Response: {result}")
except Exception as e:
    print(f"❌ Upload failed: {e}")
    sys.exit(1)

# Try to retrieve it back
print(f"\n📥 Retrieving uploaded image...")
try:
    retrieved_data = api.get_image('test_upload.png', '', 'input')
    print(f"✅ Retrieved {len(retrieved_data)} bytes")

    # Verify it's a valid image
    retrieved_image = Image.open(io.BytesIO(retrieved_data))
    print(f"   Image size: {retrieved_image.size}")
    print(f"   Image mode: {retrieved_image.mode}")

except Exception as e:
    print(f"❌ Retrieval failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All tests passed! Image upload/download works correctly.")
print("=" * 60)
