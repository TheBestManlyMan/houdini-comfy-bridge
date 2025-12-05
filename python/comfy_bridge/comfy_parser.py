"""
ComfyUI Workflow Parser
Parses ComfyUI workflow JSON files to extract input nodes and generate Houdini parameter templates.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple


class ComfyWorkflowParser:
    """Parser for ComfyUI workflow JSON files."""

    def __init__(self, workflow_path: Optional[str] = None):
        """
        Initialize workflow parser.

        Args:
            workflow_path: Path to workflow JSON file
        """
        self.workflow_path = workflow_path
        self.workflow_data = None
        self.input_nodes = {}
        self.cached_workflow = None

        if workflow_path:
            self.load_workflow(workflow_path)

    def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """
        Load workflow JSON from file.

        Args:
            workflow_path: Path to workflow JSON file

        Returns:
            Parsed workflow data

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

        with open(workflow_path, 'r') as f:
            self.workflow_data = json.load(f)

        self.workflow_path = workflow_path
        self.cached_workflow = self.workflow_data.copy()
        self._extract_input_nodes()

        return self.workflow_data

    def load_workflow_from_string(self, workflow_json: str) -> Dict[str, Any]:
        """
        Load workflow from JSON string.

        Args:
            workflow_json: JSON string containing workflow

        Returns:
            Parsed workflow data
        """
        self.workflow_data = json.loads(workflow_json)
        self.cached_workflow = self.workflow_data.copy()
        self._extract_input_nodes()

        return self.workflow_data

    def _extract_input_nodes(self) -> None:
        """Extract nodes with 'INPUT_' prefix from workflow."""
        self.input_nodes = {}

        if not self.workflow_data:
            return

        for node_id, node_data in self.workflow_data.items():
            class_type = node_data.get('class_type', '')
            title = node_data.get('_meta', {}).get('title', '')

            # Check if this is an input node (using title with INPUT_ prefix)
            if title.startswith('INPUT_'):
                input_name = title[6:]  # Remove 'INPUT_' prefix
                self.input_nodes[node_id] = {
                    'name': input_name,
                    'class_type': class_type,
                    'inputs': node_data.get('inputs', {}),
                    'node_data': node_data
                }

    def get_input_nodes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all input nodes from the workflow.

        Returns:
            Dictionary of input nodes with their metadata
        """
        return self.input_nodes

    def get_input_parameters(self) -> List[Dict[str, Any]]:
        """
        Generate parameter definitions for Houdini from input nodes.

        Returns:
            List of parameter definitions suitable for Houdini parameter templates
        """
        parameters = []

        for node_id, node_info in self.input_nodes.items():
            param_name = node_info['name']
            class_type = node_info['class_type']
            inputs = node_info['inputs']

            # Generate parameters based on class type
            param_def = self._generate_parameter_definition(
                param_name, class_type, inputs, node_id
            )

            if param_def:
                parameters.append(param_def)

        return parameters

    def _generate_parameter_definition(self, name: str, class_type: str,
                                       inputs: Dict[str, Any],
                                       node_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate a Houdini parameter definition from node information.

        Args:
            name: Parameter name
            class_type: ComfyUI node class type
            inputs: Node inputs dictionary
            node_id: Node ID in workflow

        Returns:
            Parameter definition dictionary
        """
        param_def = {
            'name': self._sanitize_name(name),
            'label': name,
            'node_id': node_id,
            'class_type': class_type
        }

        # Map common ComfyUI node types to Houdini parameter types
        type_mappings = {
            'LoadImage': {'type': 'image', 'parm_type': 'file'},
            'KSampler': {'type': 'sampler', 'parm_type': 'folder'},
            'CLIPTextEncode': {'type': 'text', 'parm_type': 'string'},
            'EmptyLatentImage': {'type': 'dimensions', 'parm_type': 'intvector2'},
            'SaveImage': {'type': 'output', 'parm_type': 'toggle'},
        }

        # Determine parameter type based on class
        if class_type in type_mappings:
            mapping = type_mappings[class_type]
            param_def['type'] = mapping['type']
            param_def['parm_type'] = mapping['parm_type']
        else:
            # Default to analyzing inputs
            param_def['type'] = 'generic'
            param_def['parm_type'] = self._infer_parm_type_from_inputs(inputs)

        # Extract default values from inputs
        param_def['default'] = self._extract_default_values(inputs)
        param_def['inputs'] = inputs

        return param_def

    def _infer_parm_type_from_inputs(self, inputs: Dict[str, Any]) -> str:
        """
        Infer Houdini parameter type from node inputs.

        Args:
            inputs: Node inputs dictionary

        Returns:
            Houdini parameter type string
        """
        # Check for common input patterns
        if 'image' in inputs:
            return 'file'
        elif 'text' in inputs:
            return 'string'
        elif 'seed' in inputs:
            return 'int'
        elif 'width' in inputs and 'height' in inputs:
            return 'intvector2'
        elif any(isinstance(v, (int, float)) for v in inputs.values()):
            return 'float'
        else:
            return 'string'

    def _extract_default_values(self, inputs: Dict[str, Any]) -> Any:
        """
        Extract default values from node inputs.

        Args:
            inputs: Node inputs dictionary

        Returns:
            Default value or values
        """
        if not inputs:
            return None

        # If single value, return it
        if len(inputs) == 1:
            return list(inputs.values())[0]

        # Return full input dict for complex cases
        return inputs

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize parameter name for Houdini.

        Args:
            name: Original parameter name

        Returns:
            Sanitized name (lowercase, underscores, no special chars)
        """
        # Replace spaces and special characters with underscores
        sanitized = ''.join(c if c.isalnum() else '_' for c in name)
        # Convert to lowercase
        sanitized = sanitized.lower()
        # Remove consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')

        return sanitized

    def update_workflow_inputs(self, input_values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update workflow with new input values.

        Args:
            input_values: Dictionary mapping input names to new values

        Returns:
            Updated workflow data
        """
        if not self.workflow_data:
            raise RuntimeError("No workflow loaded")

        # Create a deep copy to avoid modifying original
        updated_workflow = json.loads(json.dumps(self.workflow_data))

        for node_id, node_info in self.input_nodes.items():
            param_name = node_info['name']
            sanitized_name = self._sanitize_name(param_name)

            if sanitized_name in input_values:
                new_value = input_values[sanitized_name]

                # Update the node's inputs with new value
                if node_id in updated_workflow:
                    self._update_node_value(
                        updated_workflow[node_id],
                        new_value,
                        node_info['class_type']
                    )

        return updated_workflow

    def _update_node_value(self, node: Dict[str, Any], value: Any,
                          class_type: str) -> None:
        """
        Update a node's value based on its class type.

        Args:
            node: Node data to update
            value: New value
            class_type: Node class type
        """
        inputs = node.get('inputs', {})

        # Update based on class type
        if class_type == 'LoadImage':
            inputs['image'] = value
        elif class_type == 'CLIPTextEncode':
            inputs['text'] = value
        elif class_type == 'EmptyLatentImage':
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                inputs['width'] = value[0]
                inputs['height'] = value[1]
        elif class_type == 'KSampler':
            if isinstance(value, dict):
                inputs.update(value)
            elif 'seed' in inputs:
                inputs['seed'] = value
        else:
            # Generic update - try to update first input field
            if inputs:
                first_key = next(iter(inputs))
                inputs[first_key] = value

    def get_workflow_copy(self) -> Dict[str, Any]:
        """
        Get a copy of the current workflow.

        Returns:
            Deep copy of workflow data
        """
        if self.workflow_data:
            return json.loads(json.dumps(self.workflow_data))
        return {}

    def get_cached_workflow(self) -> Optional[Dict[str, Any]]:
        """
        Get cached workflow (original loaded version).

        Returns:
            Cached workflow data or None
        """
        return self.cached_workflow
