"""
Build ComfyUI COP HDA
Script to create the Houdini Digital Asset for ComfyUI integration.
"""

import hou


def create_comfy_cop_hda():
    """Create the ComfyUI COP HDA."""

    # Create a COP network if it doesn't exist
    cop_context = hou.node('/img')
    if not cop_context:
        cop_context = hou.node('/').createNode('img')

    # Create base COP node (use null as base)
    base_node = cop_context.createNode('null', 'comfy_bridge')

    # Build parameter template group
    ptg = hou.ParmTemplateGroup()

    # Add main folder
    main_folder = hou.FolderParmTemplate('main_folder', 'ComfyUI Bridge')

    # Server settings
    server_folder = hou.FolderParmTemplate('server_settings', 'Server Settings')

    server_folder.addParmTemplate(hou.StringParmTemplate(
        'comfy_host', 'ComfyUI Host',
        1,
        default_value=('127.0.0.1',),
        help='Hostname or IP address of ComfyUI server'
    ))

    server_folder.addParmTemplate(hou.IntParmTemplate(
        'comfy_port', 'ComfyUI Port',
        1,
        default_value=(8188,),
        min=1,
        max=65535,
        help='Port number of ComfyUI server'
    ))

    server_folder.addParmTemplate(hou.ButtonParmTemplate(
        'test_connection', 'Test Connection',
        help='Test connection to ComfyUI server',
        script_callback='hou.phm().test_connection_callback(kwargs["node"])',
        script_callback_language=hou.scriptLanguage.Python
    ))

    main_folder.addParmTemplate(server_folder)

    # Workflow settings
    workflow_folder = hou.FolderParmTemplate('workflow_settings', 'Workflow Settings')

    workflow_folder.addParmTemplate(hou.StringParmTemplate(
        'workflow_file', 'Workflow File',
        1,
        default_value=('',),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Any,
        help='Path to ComfyUI workflow JSON file',
        tags={
            'filechooser_pattern': '*.json',
            'script_callback': 'hou.phm().load_workflow_callback(kwargs["node"])',
            'script_callback_language': 'python'
        }
    ))

    workflow_folder.addParmTemplate(hou.ButtonParmTemplate(
        'reload_workflow', 'Reload Workflow',
        help='Reload workflow and rebuild parameters',
        script_callback='hou.phm().load_workflow_callback(kwargs["node"])',
        script_callback_language=hou.scriptLanguage.Python
    ))

    main_folder.addParmTemplate(workflow_folder)

    # Execution settings
    exec_folder = hou.FolderParmTemplate('execution_settings', 'Execution')

    exec_folder.addParmTemplate(hou.ButtonParmTemplate(
        'execute', 'Execute Workflow',
        help='Execute the workflow on ComfyUI server',
        script_callback='hou.phm().execute_workflow_callback(kwargs["node"])',
        script_callback_language=hou.scriptLanguage.Python
    ))

    exec_folder.addParmTemplate(hou.FloatParmTemplate(
        'timeout', 'Timeout',
        1,
        default_value=(300.0,),
        min=1.0,
        help='Maximum time to wait for workflow completion (seconds)'
    ))

    main_folder.addParmTemplate(exec_folder)

    # Output settings
    output_folder = hou.FolderParmTemplate('output_settings', 'Output')

    output_folder.addParmTemplate(hou.StringParmTemplate(
        'output_dir', 'Output Directory',
        1,
        default_value=('$HIP/comfy_output',),
        string_type=hou.stringParmType.FileReference,
        help='Directory to save output images'
    ))

    output_folder.addParmTemplate(hou.ToggleParmTemplate(
        'save_outputs', 'Save Outputs to Disk',
        default_value=True,
        help='Save output images to disk'
    ))

    main_folder.addParmTemplate(output_folder)

    ptg.append(main_folder)

    # Apply parameter template group
    base_node.setParmTemplateGroup(ptg)

    # Create HDA from node
    hda_path = hou.homeHoudiniDirectory() + '/otls/comfy_bridge.hda'

    # Create the HDA
    base_node.type().definition().updateFromNode(base_node)
    hda = base_node.createDigitalAsset(
        name='comfy_bridge',
        hda_file_name=hda_path,
        description='ComfyUI Bridge COP',
        min_num_inputs=0,
        max_num_inputs=1
    )

    print(f"HDA created at: {hda_path}")

    return base_node


if __name__ == '__main__':
    create_comfy_cop_hda()
