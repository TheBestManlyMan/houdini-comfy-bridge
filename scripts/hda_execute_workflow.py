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

from comfy_bridge import ComfyAPI, ComfyWorkflowParser, get_logger


def execute_workflow(node):
    """
    Execute ComfyUI workflow from Houdini COP node.

    This is the main entry point that orchestrates the workflow execution by:
    1. Validating and extracting parameters
    2. Connecting to ComfyUI server
    3. Uploading input images
    4. Executing the workflow
    5. Saving output images

    Args:
        node: The HDA node instance (hou.Node)
    """
    # Initialize logger
    verbose = node.parm('verbose').eval() if node.parm('verbose') else False
    logger = get_logger(debug=verbose)

    try:
        # 1. Validate and get parameters
        params = _get_and_validate_parameters(node, logger)

        # 2. Initialize API and parser
        api, parser = _initialize_api_and_parser(
            params['host'],
            params['port'],
            params['workflow_path'],
            verbose,
            logger
        )

        # 3. Prepare input images
        uploaded_images = _prepare_input_images(node, parser, api, logger)

        # 4. Collect parameter values
        input_values = _collect_parameter_values(node, parser, uploaded_images, logger)

        # 5. Update and execute workflow
        updated_workflow = parser.update_workflow_inputs(input_values)
        logger.debug(f"Workflow has {len(updated_workflow)} nodes")

        results = _execute_and_retrieve_results(
            api,
            updated_workflow,
            params['host'],
            params['port'],
            logger
        )

        # 6. Save output images
        _save_output_images(node, results, logger)

        # Success message
        hou.ui.setStatusMessage(
            f"Successfully executed workflow: {len(results)} image(s) generated",
            severity=hou.severityType.Message
        )

    except FileNotFoundError as e:
        _handle_error(logger, f"File not found: {str(e)}")

    except ConnectionError as e:
        _handle_error(logger, f"Connection error: {str(e)}")

    except ValueError as e:
        _handle_error(logger, f"Invalid parameter: {str(e)}")

    except Exception as e:
        _handle_error(logger, f"Execution failed: {str(e)}", show_traceback=True)


def _get_and_validate_parameters(node, logger):
    """
    Extract and validate parameters from HDA node.

    Args:
        node: HDA node instance
        logger: Logger instance

    Returns:
        dict: Validated parameters (workflow_path, host, port)

    Raises:
        ValueError: If required parameters are missing
        FileNotFoundError: If workflow file doesn't exist
    """
    # Get workflow path
    workflow_parm = node.parm('workflow_path')
    if not workflow_parm:
        available_parms = [p.name() for p in node.parms()]
        raise ValueError(
            f"Parameter 'workflow_path' not found on node '{node.path()}'. "
            f"Available parameters: {', '.join(available_parms[:20])}"
        )

    workflow_path = workflow_parm.evalAsString()
    if not workflow_path:
        raise ValueError("No workflow file specified")

    workflow_path = hou.text.expandString(workflow_path)
    if not os.path.exists(workflow_path):
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    # Get server info - support both old and new parameter styles
    server_parm = node.parm('server_address')
    port_parm = node.parm('server_port')

    if port_parm:
        # New style: separate server_address and server_port
        host = server_parm.evalAsString() if server_parm else '127.0.0.1'
        port = port_parm.eval()
    elif server_parm:
        # Old style: server_address contains "host:port"
        server_address = server_parm.evalAsString()
        if ':' in server_address:
            host, port = server_address.split(':', 1)
            port = int(port)
        else:
            host = server_address
            port = 8188
    else:
        # Default values
        host = '127.0.0.1'
        port = 8188

    logger.debug(f"Parameters validated: workflow={workflow_path}, server={host}:{port}")

    return {
        'workflow_path': workflow_path,
        'host': host,
        'port': port
    }


def _initialize_api_and_parser(host, port, workflow_path, verbose, logger):
    """
    Initialize ComfyUI API client and workflow parser.

    Args:
        host: ComfyUI server host
        port: ComfyUI server port
        workflow_path: Path to workflow JSON file
        verbose: Enable debug logging
        logger: Logger instance

    Returns:
        tuple: (ComfyAPI instance, ComfyWorkflowParser instance)

    Raises:
        ConnectionError: If cannot connect to ComfyUI server
    """
    logger.info(f"Connecting to ComfyUI at {host}:{port}")

    api = ComfyAPI(host=host, port=port, debug=verbose)

    if not api.is_server_alive():
        raise ConnectionError(
            f"Cannot connect to ComfyUI at {host}:{port}. "
            "Make sure ComfyUI is running."
        )

    logger.info("Successfully connected to ComfyUI server")
    parser = ComfyWorkflowParser(workflow_path)

    return api, parser


def _prepare_input_images(node, parser, api, logger):
    """
    Read input images from connected COP nodes and upload to ComfyUI.

    Args:
        node: HDA node instance
        parser: ComfyWorkflowParser instance
        api: ComfyAPI instance
        logger: Logger instance

    Returns:
        dict: Mapping of parameter names to uploaded filenames
    """
    # Get workflow inputs from node user data (set by hda_interface)
    workflow_inputs_json = node.userData('workflow_inputs')
    if workflow_inputs_json:
        import json
        try:
            workflow_inputs = json.loads(workflow_inputs_json)
        except (json.JSONDecodeError, TypeError):
            workflow_inputs = []
    else:
        # Fallback: use parser's input nodes
        workflow_inputs = []
        for node_id, node_info in parser.get_input_nodes().items():
            workflow_inputs.append({
                'node_id': node_id,
                'name': node_info['name'],
                'class_type': node_info.get('class_type', 'LoadImage'),
                'input_key': parser._sanitize_name(node_info['name'])
            })

    uploaded_images = {}

    for i, input_info in enumerate(workflow_inputs):
        input_node = node.input(i)
        if not input_node:
            logger.warning(f"input{i} ({input_info['name']}) not connected")
            continue

        if input_info['class_type'] != 'LoadImage':
            logger.debug(f"Skipping input{i} - not a LoadImage node")
            continue

        logger.info(f"Reading input{i} ({input_info['name']}) from: {input_node.path()}")

        try:
            # Read image from COP
            image_data = _read_cop_image_as_png(input_node)
            logger.debug(f"Read {len(image_data)} bytes from input COP")

            # Upload to ComfyUI
            filename = f"houdini_input_{i}.png"
            api.upload_image(
                image_data,
                filename=filename,
                image_type='input',
                overwrite=True
            )
            logger.info(f"Uploaded as: {filename}")

            uploaded_images[input_info['input_key']] = filename

        except Exception as e:
            logger.error(f"Failed to read/upload input{i}: {e}")
            import traceback
            traceback.print_exc()

    return uploaded_images


def _collect_parameter_values(node, parser, uploaded_images, logger):
    """
    Collect parameter values from Houdini node to pass to workflow.

    Args:
        node: HDA node instance
        parser: ComfyWorkflowParser instance
        uploaded_images: Dict of uploaded image filenames
        logger: Logger instance

    Returns:
        dict: Parameter name to value mapping
    """
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
                input_values[param_name] = parm.evalAsString()
            elif parm_type in (hou.parmTemplateType.Int, hou.parmTemplateType.Float):
                input_values[param_name] = parm.eval()
            elif parm_type == hou.parmTemplateType.Toggle:
                input_values[param_name] = bool(parm.eval())

    # Override with uploaded images for LoadImage nodes
    for param_name, filename in uploaded_images.items():
        input_values[param_name] = filename
        logger.info(f"Using uploaded image for '{param_name}': {filename}")

    logger.debug(f"Collected {len(input_values)} parameter values")
    return input_values


def _execute_and_retrieve_results(api, workflow, host, port, logger):
    """
    Execute workflow on ComfyUI server and retrieve results.

    Args:
        api: ComfyAPI instance
        workflow: Updated workflow dict
        host: Server host (for logging)
        port: Server port (for logging)
        logger: Logger instance

    Returns:
        list: List of (filename, image_data) tuples

    Raises:
        RuntimeError: If workflow returns no images
    """
    logger.info(f"Executing workflow on {host}:{port}...")

    results = api.execute_workflow(workflow, timeout=300.0)

    logger.debug(f"Results: {len(results)} image(s)")

    if not results:
        raise RuntimeError("Workflow executed but returned no images")

    logger.info(f"Received {len(results)} output image(s)")
    return results


def _save_output_images(node, results, logger):
    """
    Save output images to COP nodes.

    Args:
        node: HDA node instance
        results: List of (filename, image_data) tuples
        logger: Logger instance
    """
    for i, (filename, image_data) in enumerate(results):
        logger.debug(f"Processing image {i}: {filename}, {len(image_data)} bytes")
        _write_png_to_cop(node, image_data, plane_name=f'C' if i == 0 else f'C{i}')
        logger.info(f"Saved output {i}: {filename}")


def _handle_error(logger, error_msg, show_traceback=False):
    """
    Handle errors by logging and showing UI message.

    Args:
        logger: Logger instance
        error_msg: Error message to display
        show_traceback: Whether to print full traceback
    """
    hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
    logger.error(error_msg)

    if show_traceback:
        import traceback
        traceback.print_exc()


def _read_cop_image_as_png(cop_node):
    """
    Read COP2 node output and convert to PNG bytes.

    This function handles reading images from Houdini COP nodes. It has two
    strategies based on the COP node type:

    1. File COP nodes: Read the source file directly using PIL
       - Fast and reliable
       - Works with any image format supported by PIL
       - Supports Houdini variables (e.g., $HIP, $F)

    2. Other COP nodes (Composite, Color, etc.): NOT YET IMPLEMENTED
       - Would require using mwrite command or similar
       - Requires X11 display in headless environments
       - Currently raises NotImplementedError

    Workaround for non-File COPs:
    - Use a File COP node as input
    - Or render your COPs to disk first, then use File COP to read them

    Args:
        cop_node: Houdini COP2 node

    Returns:
        bytes: PNG image data

    Raises:
        FileNotFoundError: If File COP source doesn't exist
        NotImplementedError: If trying to read from non-File COP
    """
    import tempfile
    from PIL import Image

    logger = get_logger()

    # Force cook the node to ensure image is loaded
    cop_node.cook(force=True)

    # Strategy 1: File COP - read source file directly
    if cop_node.type().name() == 'file':
        file_path_parm = cop_node.parm('filename1')
        if not file_path_parm:
            raise ValueError(f"File COP {cop_node.path()} has no filename1 parameter")

        file_path = file_path_parm.evalAsString()
        file_path = hou.text.expandString(file_path)  # Expand $HIP, $F, etc.

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File COP source not found: {file_path}")

        logger.debug(f"Reading directly from File COP: {file_path}")

        # Read and convert using PIL
        pil_image = Image.open(file_path)

        # Convert RGBA to RGB (ComfyUI typically expects RGB)
        if pil_image.mode == 'RGBA':
            pil_image = pil_image.convert('RGB')

        # Convert to PNG bytes
        png_buffer = io.BytesIO()
        pil_image.save(png_buffer, format='PNG')
        return png_buffer.getvalue()

    # Strategy 2: Other COP types - not yet implemented
    # Would require: hou.hscript(f"mwrite {cop_node.path()} {output_path}")
    # But this needs X11 display in headless mode
    logger.error(f"Non-File COP nodes not supported: {cop_node.type().name()}")
    logger.error("Workaround: Use a File COP to load your image")

    raise NotImplementedError(
        f"Reading from {cop_node.type().name()} COP nodes is not yet supported.\n\n"
        "Current workaround:\n"
        "1. Render your COP to disk first\n"
        "2. Use a File COP node to load the rendered image\n"
        "3. Connect the File COP to this node\n\n"
        "Future implementation will support direct COP reading via mwrite."
    )


def _write_png_to_cop(node, png_data, plane_name='C'):
    """
    Write PNG image data to COP2 node output.

    This function attempts two strategies:
    1. Create an internal File COP node (works when HDA is unlocked)
    2. Save to project render directory (fallback when HDA is locked)

    Args:
        node: The HDA node instance
        png_data: PNG image bytes
        plane_name: Name of the color plane (default: 'C' for color)
    """
    import tempfile
    import shutil

    logger = get_logger()

    # Write PNG to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        tmp_file.write(png_data)
        tmp_path = tmp_file.name

    try:
        # Strategy 1: Try to create internal file node
        # This works when the HDA is unlocked (development mode)
        file_node = _get_or_create_file_node(node)

        if file_node:
            file_node.parm('filename1').set(tmp_path)
            file_node.cook()
            logger.info(f"Loaded result into internal File COP: {tmp_path}")
            return

        # Strategy 2: Fallback - save to project directory
        # This is used when HDA is locked or internal node creation fails
        output_path = _save_to_fallback_location(node, tmp_path)
        logger.info(f"HDA is locked, saved to: {output_path}")
        logger.info("To view: Load this file manually in a File COP node")

    except Exception as e:
        logger.warning(f"Could not create internal File COP: {e}")

        # Fallback - save to project directory
        output_path = _save_to_fallback_location(node, tmp_path)
        logger.info(f"HDA is locked, saved to: {output_path}")
        logger.info("To view: Load this file manually in a File COP node")

    finally:
        # Clean up temp file (only if it wasn't moved)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass


def _get_or_create_file_node(node):
    """
    Get existing or create new File COP node inside HDA.

    Args:
        node: HDA node instance

    Returns:
        File COP node or None if creation fails
    """
    # Try to find existing file node
    for child in node.children():
        if child.type().name() == 'file':
            return child

    # Try to create new file node
    try:
        return node.createNode('file', 'comfy_result')
    except:
        return None


def _save_to_fallback_location(node, tmp_path):
    """
    Save output to fallback location when HDA is locked.

    Uses $HIP/render/comfyui/ as the fallback directory.

    Args:
        node: HDA node instance
        tmp_path: Path to temporary file

    Returns:
        str: Path where file was saved
    """
    import shutil

    # Use $HIP/render/comfyui/ as fallback (more portable than ~/comfyui_output)
    hip_dir = hou.text.expandString('$HIP')

    # Fallback to home if HIP is not set
    if not hip_dir or hip_dir == '$HIP':
        output_dir = os.path.expanduser('~/comfyui_output')
    else:
        output_dir = os.path.join(hip_dir, 'render', 'comfyui')

    os.makedirs(output_dir, exist_ok=True)

    # Generate timestamped filename to avoid collisions
    import time
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f"comfyui_result_{timestamp}.png"
    output_path = os.path.join(output_dir, filename)

    # Move temp file to output directory
    shutil.move(tmp_path, output_path)

    return output_path
