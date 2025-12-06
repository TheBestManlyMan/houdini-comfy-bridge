"""
Execute workflow function for ComfyUI Bridge HDA
Copy this into the PythonModule section of your HDA
"""

import hou
import sys
import os
import io

# Ensure comfy_bridge is in path (should be set via houdini.env, but verify)
# Use relative path from script location for portability
bridge_path = os.path.join(os.path.dirname(__file__), '..', 'python')
bridge_path = os.path.abspath(bridge_path)
if bridge_path not in sys.path:
    sys.path.insert(0, bridge_path)

from comfy_bridge import ComfyAPI, ComfyWorkflowParser


def execute_workflow(node):
    """
    Execute ComfyUI workflow from Houdini COP node.

    Args:
        node: The HDA node instance (hou.Node)
    """
    try:
        # 1. Get parameters from node
        # Check if parameters exist first
        workflow_parm = node.parm('workflow_path')
        server_parm = node.parm('server_address')

        if not workflow_parm:
            # Debug: show available parameters
            available_parms = [p.name() for p in node.parms()]
            raise ValueError(f"Parameter 'workflow_path' not found on node '{node.path()}'. "
                           f"Available parameters: {', '.join(available_parms[:20])}")

        if not server_parm:
            available_parms = [p.name() for p in node.parms()]
            raise ValueError(f"Parameter 'server_address' not found on node '{node.path()}'. "
                           f"Available parameters: {', '.join(available_parms[:20])}")

        workflow_path = workflow_parm.evalAsString()
        server_address = server_parm.evalAsString()

        # Validate parameters
        if not workflow_path:
            raise ValueError("No workflow file specified")

        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

        # Parse server address (format: host:port or just host)
        if ':' in server_address:
            host, port = server_address.split(':', 1)
            port = int(port)
        else:
            host = server_address
            port = 8188

        # 2. Initialize API and parser
        api = ComfyAPI(host=host, port=port)

        # Test server connection
        if not api.is_server_alive():
            raise ConnectionError(f"Cannot connect to ComfyUI at {host}:{port}. "
                                "Make sure ComfyUI is running.")

        parser = ComfyWorkflowParser(workflow_path)

        # 3. Read input image from COP (if connected)
        input_image_data = None
        input_node = node.input(0)

        if input_node:
            print(f"Reading input image from: {input_node.path()}")
            try:
                # Get the source image from input
                input_image_data = _read_cop_image_as_png(input_node)
                print(f"Read {len(input_image_data)} bytes from input COP")

                # Upload to ComfyUI
                upload_result = api.upload_image(
                    input_image_data,
                    filename='houdini_input.png',
                    image_type='input',
                    overwrite=True
                )
                print(f"Uploaded input image: {upload_result}")
            except Exception as e:
                print(f"Warning: Failed to read/upload input image: {e}")
                import traceback
                traceback.print_exc()
                input_image_data = None
        else:
            print("No input node connected")

        # 4. Build parameter values dict from Houdini parameters
        input_values = {}
        input_nodes = parser.get_input_nodes()

        for node_id, node_info in input_nodes.items():
            param_name = parser._sanitize_name(node_info['name'])

            # Check if this parameter exists on the Houdini node
            parm = node.parm(param_name)
            if parm:
                # Get value based on parameter type
                parm_template = parm.parmTemplate()
                parm_type = parm_template.type()

                if parm_type == hou.parmTemplateType.String:
                    input_values[param_name] = parm.eval()
                elif parm_type == hou.parmTemplateType.Int:
                    if parm_template.numComponents() > 1:
                        input_values[param_name] = parm.eval()
                    else:
                        input_values[param_name] = parm.eval()
                elif parm_type == hou.parmTemplateType.Float:
                    if parm_template.numComponents() > 1:
                        input_values[param_name] = parm.eval()
                    else:
                        input_values[param_name] = parm.eval()
                elif parm_type == hou.parmTemplateType.Toggle:
                    input_values[param_name] = bool(parm.eval())

        # If we uploaded an image, add it to input_values for LoadImage nodes
        if input_image_data:
            for node_id, node_info in input_nodes.items():
                if node_info['class_type'] == 'LoadImage':
                    param_name = parser._sanitize_name(node_info['name'])
                    input_values[param_name] = 'houdini_input.png'
                    print(f"Setting LoadImage node '{node_info['name']}' to use: houdini_input.png")

        # 5. Update workflow with parameter values
        print(f"[DEBUG] Input values to update: {input_values}")
        updated_workflow = parser.update_workflow_inputs(input_values)

        # Debug: Save updated workflow
        print(f"[DEBUG] Updated workflow node count: {len(updated_workflow)}")
        print(f"[DEBUG] Updated workflow keys: {list(updated_workflow.keys())[:5]}")

        # 6. Execute workflow
        print("=" * 60)
        print("=== DEBUG: Request to ComfyUI ===")
        print(f"URL: http://{host}:{port}/prompt")
        print(f"Workflow node count: {len(updated_workflow)}")
        print(f"Workflow structure:")
        for node_id, node_data in list(updated_workflow.items())[:3]:
            if isinstance(node_data, dict):
                print(f"  Node {node_id}: {node_data.get('class_type', 'unknown')}")
            else:
                print(f"  Node {node_id}: {type(node_data)} - {node_data}")
                continue

        # Save workflow to file for inspection
        import json
        workflow_debug_path = '/tmp/workflow_debug.json'
        try:
            with open(workflow_debug_path, 'w') as f:
                json.dump(updated_workflow, f, indent=2)
            print(f"Full workflow saved to: {workflow_debug_path}")
        except Exception as e:
            print(f"Could not save workflow debug file: {e}")

        print("=" * 60)

        print(f"Executing workflow on {host}:{port}...")
        results = api.execute_workflow(updated_workflow, timeout=300.0)

        print(f"[DEBUG] Results type: {type(results)}")
        print(f"[DEBUG] Results content: {results}")

        if not results:
            raise RuntimeError("Workflow executed but returned no images")

        print(f"Received {len(results)} output image(s)")

        # 7. Write results to COP output
        for i, (filename, image_data) in enumerate(results):
            print(f"[DEBUG] Processing image {i}: {filename}, data size: {len(image_data)} bytes")
            _write_png_to_cop(node, image_data, plane_name=f'C' if i == 0 else f'C{i}')
            print(f"Wrote output {i}: {filename}")

        # Success message
        hou.ui.setStatusMessage(f"Successfully executed workflow: {len(results)} image(s) generated",
                               severity=hou.severityType.Message)

    except FileNotFoundError as e:
        error_msg = f"File not found: {str(e)}"
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        print(f"ERROR: {error_msg}")

    except ConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        print(f"ERROR: {error_msg}")

    except ValueError as e:
        error_msg = f"Invalid parameter: {str(e)}"
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        print(f"ERROR: {error_msg}")

    except Exception as e:
        error_msg = f"Execution failed: {str(e)}"
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()


def _read_cop_image_as_png(cop_node):
    """
    Read COP2 node output and convert to PNG bytes.

    For File nodes: reads the source file directly
    For other nodes: uses Mantra cop output

    Args:
        cop_node: Houdini COP2 node

    Returns:
        bytes: PNG image data
    """
    import tempfile
    from PIL import Image

    # Force cook the node to ensure image is loaded
    cop_node.cook(force=True)

    # Check if this is a File COP - if so, just read the file directly
    if cop_node.type().name() == 'file':
        # Get the file path from the file node
        file_path_parm = cop_node.parm('filename1')
        if file_path_parm:
            file_path = file_path_parm.evalAsString()
            file_path = hou.text.expandString(file_path)  # Expand variables

            if os.path.exists(file_path):
                print(f"Reading directly from File COP source: {file_path}")
                # Read the file directly
                pil_image = Image.open(file_path)

                # Convert to RGB if needed
                if pil_image.mode == 'RGBA':
                    pil_image = pil_image.convert('RGB')

                # Save to BytesIO as PNG
                png_buffer = io.BytesIO()
                pil_image.save(png_buffer, format='PNG')
                return png_buffer.getvalue()
            else:
                raise FileNotFoundError(f"File COP source file not found: {file_path}")

    # For non-File nodes, we need to save the output
    # Create temporary file for intermediate save
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Use Mantra to render the COP to a file
        # This is a workaround since we can't save COP images directly
        print(f"[WARNING] Non-File COP nodes not fully supported yet")
        print(f"[WARNING] Please use a File COP node for input images")
        raise NotImplementedError("Non-File COP nodes not supported yet. Use a File COP node.")

        # Placeholder for future implementation
        # Could use: hou.hscript(f"mwrite {cop_node.path()} {tmp_path}")

        # Read with PIL and convert to PNG bytes in memory
        pil_image = Image.open(tmp_path)

        # Convert to RGB if needed (remove alpha channel if present)
        if pil_image.mode == 'RGBA':
            pil_image = pil_image.convert('RGB')

        # Save to BytesIO as PNG
        png_buffer = io.BytesIO()
        pil_image.save(png_buffer, format='PNG')
        png_data = png_buffer.getvalue()

        return png_data

    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _write_png_to_cop(node, png_data, plane_name='C'):
    """
    Write PNG image data to COP2 node output.

    Args:
        node: The HDA node instance
        png_data: PNG image bytes
        plane_name: Name of the color plane (default: 'C' for color)
    """
    import tempfile

    # Write PNG to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        tmp_file.write(png_data)
        tmp_path = tmp_file.name

    try:
        # For COP nodes, we need to load the image through a File node approach
        # This is a simplified version - in a real HDA you'd set up internal
        # network structure to handle this properly

        # Get or create internal file node
        file_node = None
        for child in node.children():
            if child.type().name() == 'file':
                file_node = child
                break

        if not file_node:
            # Create a file node inside the HDA to load the result
            file_node = node.createNode('file', 'comfy_result')

        # Set the file path
        file_node.parm('filename1').set(tmp_path)

        # Cook to load the image
        file_node.cook()

        print(f"Loaded result image from {tmp_path}")

    except Exception as e:
        # HDA is likely locked - save to a known location instead
        output_dir = os.path.expanduser('~/comfyui_output')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, os.path.basename(tmp_path))

        # Move temp file to output directory
        import shutil
        shutil.move(tmp_path, output_path)

        print(f"[OUTPUT] HDA is locked, saved to: {output_path}")
        print(f"[OUTPUT] To view: Load this file manually in a File COP node")
        return

    finally:
        # Clean up after successful load
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
