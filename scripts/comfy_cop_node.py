"""
Houdini COP Node for ComfyUI Integration
Main implementation for the ComfyUI COP node with dynamic parameter generation.
"""

import hou
import os
import sys
import json
from typing import Dict, Any, List, Optional


# Add python module path
module_path = os.path.join(os.path.dirname(__file__), '..', 'python')
if module_path not in sys.path:
    sys.path.insert(0, module_path)


from comfy_bridge import ComfyAPI, ComfyWorkflowParser


class ComfyCOPNode:
    """Handler for ComfyUI COP node operations."""

    def __init__(self, node: hou.Node):
        """
        Initialize COP node handler.

        Args:
            node: Houdini node instance
        """
        self.node = node
        self.parser = None
        self.api = None

    def load_workflow(self, workflow_path: str) -> bool:
        """
        Load workflow and regenerate parameters.

        Args:
            workflow_path: Path to workflow JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load and parse workflow
            self.parser = ComfyWorkflowParser(workflow_path)

            # Store workflow path
            if self.node.parm('workflow_file'):
                self.node.parm('workflow_file').set(workflow_path)

            return True

        except Exception as e:
            hou.ui.displayMessage(
                f"Failed to load workflow: {str(e)}",
                severity=hou.severityType.Error
            )
            return False

    def rebuild_parameters(self) -> None:
        """Rebuild node parameters based on loaded workflow."""
        if not self.parser:
            return

        try:
            # Get parameter definitions from parser
            param_defs = self.parser.get_input_parameters()

            # Build parameter template group
            ptg = self.node.parmTemplateGroup()

            # Remove old dynamic parameters (keep core ones)
            self._remove_dynamic_parameters(ptg)

            # Add new dynamic parameters
            folder = hou.FolderParmTemplate('workflow_inputs', 'Workflow Inputs')

            for param_def in param_defs:
                parm_template = self._create_parameter_template(param_def)
                if parm_template:
                    folder.addParmTemplate(parm_template)

            # Add folder to template group
            ptg.append(folder)

            # Apply new template group
            self.node.setParmTemplateGroup(ptg)

        except Exception as e:
            hou.ui.displayMessage(
                f"Failed to rebuild parameters: {str(e)}",
                severity=hou.severityType.Error
            )

    def _remove_dynamic_parameters(self, ptg: hou.ParmTemplateGroup) -> None:
        """
        Remove dynamically created parameters.

        Args:
            ptg: Parameter template group
        """
        # Remove workflow inputs folder if it exists
        try:
            ptg.remove('workflow_inputs')
        except hou.OperationFailed:
            pass

    def _create_parameter_template(self, param_def: Dict[str, Any]) -> Optional[hou.ParmTemplate]:
        """
        Create a Houdini parameter template from parameter definition.

        Args:
            param_def: Parameter definition dictionary

        Returns:
            Houdini parameter template or None
        """
        name = param_def['name']
        label = param_def['label']
        parm_type = param_def.get('parm_type', 'string')
        default = param_def.get('default', None)

        try:
            if parm_type == 'string':
                return hou.StringParmTemplate(
                    name, label,
                    1,
                    default_value=(str(default),) if default else ('',)
                )

            elif parm_type == 'file':
                template = hou.StringParmTemplate(
                    name, label,
                    1,
                    default_value=(str(default),) if default else ('',),
                    string_type=hou.stringParmType.FileReference
                )
                return template

            elif parm_type == 'int':
                return hou.IntParmTemplate(
                    name, label,
                    1,
                    default_value=(int(default),) if default else (0,)
                )

            elif parm_type == 'float':
                return hou.FloatParmTemplate(
                    name, label,
                    1,
                    default_value=(float(default),) if default else (0.0,)
                )

            elif parm_type == 'intvector2':
                defaults = (512, 512)
                if isinstance(default, (list, tuple)) and len(default) >= 2:
                    defaults = (int(default[0]), int(default[1]))
                elif isinstance(default, dict):
                    defaults = (
                        int(default.get('width', 512)),
                        int(default.get('height', 512))
                    )

                return hou.IntParmTemplate(
                    name, label,
                    2,
                    default_value=defaults
                )

            elif parm_type == 'toggle':
                return hou.ToggleParmTemplate(
                    name, label,
                    default_value=bool(default) if default else False
                )

            else:
                # Default to string
                return hou.StringParmTemplate(
                    name, label,
                    1,
                    default_value=(str(default),) if default else ('',)
                )

        except Exception as e:
            print(f"Error creating parameter template for {name}: {e}")
            return None

    def execute_workflow(self) -> List[bytes]:
        """
        Execute the workflow with current parameter values.

        Returns:
            List of output image data
        """
        if not self.parser:
            raise RuntimeError("No workflow loaded")

        # Initialize API if needed
        if not self.api:
            host = self.node.parm('comfy_host').eval() if self.node.parm('comfy_host') else '127.0.0.1'
            port = self.node.parm('comfy_port').eval() if self.node.parm('comfy_port') else 8188
            self.api = ComfyAPI(host, port)

        # Check if server is alive
        if not self.api.is_server_alive():
            raise RuntimeError(f"ComfyUI server not responding at {self.api.base_url}")

        # Collect current parameter values
        input_values = self._collect_input_values()

        # Update workflow with parameter values
        workflow = self.parser.update_workflow_inputs(input_values)

        # Execute workflow
        results = self.api.execute_workflow(workflow)

        return [img_data for _, img_data in results]

    def _collect_input_values(self) -> Dict[str, Any]:
        """
        Collect current values from dynamic parameters.

        Returns:
            Dictionary of parameter values
        """
        input_values = {}

        if not self.parser:
            return input_values

        param_defs = self.parser.get_input_parameters()

        for param_def in param_defs:
            name = param_def['name']
            parm_type = param_def.get('parm_type', 'string')

            try:
                parm = self.node.parm(name)

                if not parm:
                    continue

                if parm_type == 'intvector2':
                    # Get both components
                    parm_x = self.node.parm(name + 'x')
                    parm_y = self.node.parm(name + 'y')
                    if parm_x and parm_y:
                        input_values[name] = [parm_x.eval(), parm_y.eval()]
                elif parm_type in ('int', 'float', 'toggle'):
                    input_values[name] = parm.eval()
                else:
                    input_values[name] = parm.evalAsString()

            except Exception as e:
                print(f"Error collecting value for {name}: {e}")

        return input_values


def load_workflow_callback(node: hou.Node) -> None:
    """
    Callback when workflow file parameter changes.

    Args:
        node: Houdini node instance
    """
    workflow_path = node.parm('workflow_file').evalAsString()

    if not workflow_path or not os.path.exists(workflow_path):
        return

    handler = ComfyCOPNode(node)
    if handler.load_workflow(workflow_path):
        handler.rebuild_parameters()


def execute_workflow_callback(node: hou.Node) -> None:
    """
    Callback for execute button.

    Args:
        node: Houdini node instance
    """
    handler = ComfyCOPNode(node)

    try:
        # Get workflow path
        workflow_path = node.parm('workflow_file').evalAsString()

        if not workflow_path:
            hou.ui.displayMessage(
                "No workflow file specified",
                severity=hou.severityType.Warning
            )
            return

        # Load workflow if not already loaded
        if not handler.parser:
            if not handler.load_workflow(workflow_path):
                return

        # Execute workflow
        with hou.InterruptableOperation(
            "Executing ComfyUI workflow",
            open_interrupt_dialog=True
        ) as operation:
            results = handler.execute_workflow()

            hou.ui.displayMessage(
                f"Workflow executed successfully!\nReceived {len(results)} output image(s).",
                severity=hou.severityType.Message
            )

            # Force cook to update output
            node.cook(force=True)

    except Exception as e:
        hou.ui.displayMessage(
            f"Workflow execution failed: {str(e)}",
            severity=hou.severityType.Error
        )


def test_connection_callback(node: hou.Node) -> None:
    """
    Test connection to ComfyUI server.

    Args:
        node: Houdini node instance
    """
    host = node.parm('comfy_host').evalAsString() if node.parm('comfy_host') else '127.0.0.1'
    port = node.parm('comfy_port').eval() if node.parm('comfy_port') else 8188

    api = ComfyAPI(host, port)

    if api.is_server_alive():
        hou.ui.displayMessage(
            f"Successfully connected to ComfyUI at {api.base_url}",
            severity=hou.severityType.Message
        )
    else:
        hou.ui.displayMessage(
            f"Failed to connect to ComfyUI at {api.base_url}\nMake sure ComfyUI is running.",
            severity=hou.severityType.Error
        )
