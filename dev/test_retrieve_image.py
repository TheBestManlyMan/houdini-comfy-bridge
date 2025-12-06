#!/usr/bin/env python3
"""Test retrieving the image from the last execution"""

import sys
import os

# Add parent directory's python module to path (relative to this script)
bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
bridge_path = os.path.abspath(bridge_path)
sys.path.insert(0, bridge_path)

from comfy_bridge import ComfyAPI

# Connect to ComfyUI
api = ComfyAPI(host='127.0.0.1', port=8188)

# Get the most recent prompt_id from history
prompt_id = "8e702daa-16df-4852-bf3e-f36470a2495d"

print(f"Testing image retrieval for prompt: {prompt_id}")
print("=" * 60)

# Get history
history = api.get_history(prompt_id)
print(f"History status: {history.get('status') if history else 'None'}")

# Get outputs
outputs = history.get('outputs', {})
print(f"Outputs: {outputs}")

# Try to download the image
if outputs:
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            for img_info in node_output['images']:
                filename = img_info['filename']
                subfolder = img_info.get('subfolder', '')
                folder_type = img_info.get('type', 'output')

                print(f"\nDownloading: {filename}")
                try:
                    image_data = api.get_image(filename, subfolder, folder_type)
                    print(f"Success! Downloaded {len(image_data)} bytes")
                except Exception as e:
                    print(f"Failed: {e}")
else:
    print("No outputs found!")
