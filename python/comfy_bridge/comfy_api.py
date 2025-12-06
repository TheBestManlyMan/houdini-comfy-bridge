"""
ComfyUI API Communication Layer
Handles HTTP requests to ComfyUI REST API for image upload, workflow execution, and result fetching.
"""

import json
import urllib.request
import urllib.error
import io
import uuid
import time
from typing import Dict, List, Optional, Tuple, Any


class ComfyAPI:
    """Client for communicating with ComfyUI REST API."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        """
        Initialize ComfyUI API client.

        Args:
            host: ComfyUI server host
            port: ComfyUI server port
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.client_id = str(uuid.uuid4())

    def is_server_alive(self) -> bool:
        """
        Check if ComfyUI server is running and responsive.

        Returns:
            True if server is alive, False otherwise
        """
        try:
            req = urllib.request.Request(f"{self.base_url}/system_stats")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return False

    def upload_image(self, image_data: bytes, filename: str = "input.png",
                     image_type: str = "input", overwrite: bool = True) -> Dict[str, Any]:
        """
        Upload an image to ComfyUI server.

        Args:
            image_data: Raw image bytes
            filename: Name for the uploaded file
            image_type: Type of image ('input', 'temp', etc.)
            overwrite: Whether to overwrite existing file

        Returns:
            Response from server with upload details
        """
        # Prepare multipart form data
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        body = io.BytesIO()

        # Add image field
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode())
        body.write(b'Content-Type: image/png\r\n\r\n')
        body.write(image_data)
        body.write(b'\r\n')

        # Add type field
        body.write(f'--{boundary}\r\n'.encode())
        body.write(b'Content-Disposition: form-data; name="type"\r\n\r\n')
        body.write(image_type.encode())
        body.write(b'\r\n')

        # Add overwrite field
        body.write(f'--{boundary}\r\n'.encode())
        body.write(b'Content-Disposition: form-data; name="overwrite"\r\n\r\n')
        body.write(str(overwrite).lower().encode())
        body.write(b'\r\n')

        body.write(f'--{boundary}--\r\n'.encode())

        # Send request
        req = urllib.request.Request(
            f"{self.base_url}/upload/image",
            data=body.getvalue(),
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            }
        )

        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())

    def queue_prompt(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Queue a workflow for execution.

        Args:
            workflow: ComfyUI workflow JSON

        Returns:
            Response containing prompt_id and queue position
        """
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }

        # Debug logging
        print(f"[DEBUG] Sending to {self.base_url}/prompt")
        print(f"[DEBUG] Client ID: {self.client_id}")
        print(f"[DEBUG] Workflow keys: {list(workflow.keys())[:10]}")
        print(f"[DEBUG] Payload structure: prompt={type(workflow).__name__}, client_id=str")

        # Save payload to file for debugging
        debug_path = '/tmp/comfyui_payload_debug.json'
        try:
            with open(debug_path, 'w') as f:
                json.dump(payload, f, indent=2)
            print(f"[DEBUG] Full payload saved to: {debug_path}")
        except Exception as e:
            print(f"[DEBUG] Could not save debug file: {e}")

        req = urllib.request.Request(
            f"{self.base_url}/prompt",
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No error body"
            print(f"[ERROR] HTTP {e.code}: {e.reason}")
            print(f"[ERROR] Response body: {error_body}")
            raise

    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution history for a specific prompt.

        Args:
            prompt_id: ID of the queued prompt

        Returns:
            History data or None if not found
        """
        req = urllib.request.Request(f"{self.base_url}/history/{prompt_id}")

        try:
            with urllib.request.urlopen(req) as response:
                history = json.loads(response.read().decode())
                return history.get(prompt_id)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def wait_for_completion(self, prompt_id: str, timeout: float = 300.0,
                           poll_interval: float = 0.5) -> Dict[str, Any]:
        """
        Wait for a queued prompt to complete execution.

        Args:
            prompt_id: ID of the queued prompt
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks

        Returns:
            Final history data

        Raises:
            TimeoutError: If execution doesn't complete within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)

            if history is not None:
                # Check if execution is complete
                status = history.get('status', {})
                if status.get('completed', False) or 'outputs' in history:
                    return history

                # Check for errors
                if status.get('status_str') == 'error':
                    error_details = status.get('messages', [])
                    raise RuntimeError(f"Workflow execution failed: {error_details}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Workflow execution timed out after {timeout}s")

    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """
        Download an image from ComfyUI server.

        Args:
            filename: Name of the image file
            subfolder: Subfolder path
            folder_type: Type of folder ('output', 'input', 'temp')

        Returns:
            Raw image bytes
        """
        params = urllib.parse.urlencode({
            'filename': filename,
            'subfolder': subfolder,
            'type': folder_type
        })

        req = urllib.request.Request(f"{self.base_url}/view?{params}")

        with urllib.request.urlopen(req) as response:
            return response.read()

    def execute_workflow(self, workflow: Dict[str, Any],
                        timeout: float = 300.0) -> List[Tuple[str, bytes]]:
        """
        Execute a workflow and retrieve all output images.

        Args:
            workflow: ComfyUI workflow JSON
            timeout: Maximum time to wait for completion

        Returns:
            List of tuples containing (filename, image_data)
        """
        # Queue the workflow
        queue_result = self.queue_prompt(workflow)
        prompt_id = queue_result.get('prompt_id')

        if not prompt_id:
            raise RuntimeError("Failed to queue workflow - no prompt_id returned")

        # Wait for completion
        history = self.wait_for_completion(prompt_id, timeout)

        print(f"[API DEBUG] History keys: {history.keys() if history else 'None'}")
        print(f"[API DEBUG] History status: {history.get('status') if history else 'None'}")

        # Extract output images
        outputs = history.get('outputs', {})
        print(f"[API DEBUG] Outputs: {outputs}")
        images = []

        for node_id, node_output in outputs.items():
            print(f"[API DEBUG] Node {node_id} output: {node_output}")
            if 'images' in node_output:
                for img_info in node_output['images']:
                    filename = img_info['filename']
                    subfolder = img_info.get('subfolder', '')
                    folder_type = img_info.get('type', 'output')

                    print(f"[API DEBUG] Downloading: {filename} from {folder_type}/{subfolder}")
                    image_data = self.get_image(filename, subfolder, folder_type)
                    print(f"[API DEBUG] Downloaded {len(image_data)} bytes")
                    images.append((filename, image_data))

        print(f"[API DEBUG] Total images retrieved: {len(images)}")
        return images

    def get_queue_info(self) -> Dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Queue information including pending and running items
        """
        req = urllib.request.Request(f"{self.base_url}/queue")

        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())

    def interrupt_execution(self) -> None:
        """Interrupt current execution."""
        req = urllib.request.Request(
            f"{self.base_url}/interrupt",
            data=b'',
            method='POST'
        )

        with urllib.request.urlopen(req) as response:
            response.read()
