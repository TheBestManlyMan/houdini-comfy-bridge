"""
ComfyUI Workflow Parser
Parses ComfyUI workflow JSON files to extract input nodes and generate Houdini parameter templates.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple

from .logger import BridgeLogger


class ComfyWorkflowParser:
    """Parser for ComfyUI workflow JSON files."""

    def __init__(self, workflow_path: Optional[str] = None, debug: bool = False):
        """
        Initialize workflow parser.

        Args:
            workflow_path: Path to workflow JSON file
            debug: Enable debug logging
        """
        self.workflow_path = workflow_path
        self.workflow_data = None
        self.input_nodes = {}
        self.cached_workflow = None
        self.logger = BridgeLogger(name="comfy_parser", debug=debug)

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
            raw_data = json.load(f)

        # Convert from frontend format to API format if needed
        self.workflow_data = self._convert_to_api_format(raw_data)

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
        raw_data = json.loads(workflow_json)

        # Convert from frontend format to API format if needed
        self.workflow_data = self._convert_to_api_format(raw_data)
        self.cached_workflow = self.workflow_data.copy()
        self._extract_input_nodes()

        return self.workflow_data

    def _convert_to_api_format(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ComfyUI frontend format to API format if needed.

        ComfyUI has two JSON export formats:
        1. Frontend format: {nodes: [...], links: [...], ...}
           - Used by the visual editor
           - Contains UI layout information
           - Has separate widgets_values array

        2. API format: {node_id: {class_type: ..., inputs: {...}}, ...}
           - Used by the REST API
           - Flatter structure, no UI info
           - Values embedded directly in inputs

        This method converts format #1 to #2 if needed.

        Args:
            workflow_data: Raw workflow data

        Returns:
            Workflow in API format
        """
        # Check if already in API format (no 'nodes' key)
        if 'nodes' not in workflow_data:
            self.logger.debug("Workflow already in API format")
            return workflow_data

        self.logger.info("Converting from frontend format to API format")

        # Extract nodes and links
        nodes = workflow_data.get('nodes', [])
        links = workflow_data.get('links', [])

        # Build link lookup table for resolving node connections
        link_map = self._build_link_map(links)

        # Convert nodes to API format
        api_workflow = {}

        for node in nodes:
            node_id = str(node['id'])
            class_type = node.get('type', '')

            # Skip nodes without a type
            if not class_type:
                self.logger.warning(f"Skipping node {node_id} - no class_type")
                continue

            # Match widget values to inputs
            inputs = self._match_widgets_to_inputs(
                node.get('inputs', []),
                node.get('widgets_values', []),
                link_map
            )

            # Store node in API format
            api_workflow[node_id] = {
                'class_type': class_type,
                'inputs': inputs
            }

            # Store title in _meta for INPUT_ detection
            title = self._extract_node_title(node)
            if title:
                api_workflow[node_id]['_meta'] = {'title': title}

        self.logger.info(f"Converted {len(api_workflow)} nodes to API format")
        return api_workflow

    def _build_link_map(self, links: List[Any]) -> Dict[int, List[Any]]:
        """
        Build a lookup table for node connections.

        Args:
            links: List of link arrays from frontend format

        Returns:
            Dict mapping link_id to [source_node_id, source_slot]
        """
        link_map = {}
        for link in links:
            # Link format: [link_id, source_node, source_slot, target_node, target_slot, type]
            if len(link) >= 3:
                link_id = link[0]
                source_node = link[1]
                source_slot = link[2]
                link_map[link_id] = [str(source_node), source_slot]

        self.logger.debug(f"Built link map with {len(link_map)} connections")
        return link_map

    def _extract_node_title(self, node: Dict[str, Any]) -> str:
        """
        Extract the title from a node.

        Args:
            node: Node dictionary from frontend format

        Returns:
            Node title string or empty string
        """
        # Try direct title field
        title = node.get('title', '')

        # Also check properties.cnr_id which might contain INPUT_ prefix
        if not title and 'properties' in node:
            title = node['properties'].get('cnr_id', '')

        return title

    def _match_widgets_to_inputs(
        self,
        input_defs: List[Dict[str, Any]],
        widget_values: List[Any],
        link_map: Dict[int, List[Any]]
    ) -> Dict[str, Any]:
        """
        Match widget values to input definitions by type.

        ComfyUI frontend format stores widget values in a flat array separate
        from input definitions. This function matches them up by iterating
        through both arrays and using type compatibility checking.

        Algorithm:
        1. For each input definition:
           a. If it has a link (connection), use the link
           b. If it has a widget, find the next matching widget value by type
           c. If no match found, use next value anyway (fallback)
        2. Widget values are "consumed" - each is used only once

        Args:
            input_defs: List of input definitions from node
            widget_values: List of widget values from node
            link_map: Lookup table for node connections

        Returns:
            Dict mapping input names to values (either links or widget values)
        """
        inputs = {}
        widget_index = 0

        for input_def in input_defs:
            input_name = input_def.get('name')
            input_type = input_def.get('type')
            link_id = input_def.get('link')

            # Case 1: Input is connected to another node
            if link_id is not None and link_id in link_map:
                inputs[input_name] = link_map[link_id]
                self.logger.debug(f"Input '{input_name}' connected via link {link_id}")
                continue

            # Case 2: Input has a widget (UI control)
            if 'widget' not in input_def:
                continue

            # Try to find a type-compatible widget value
            match_result = self._find_next_compatible_widget(
                widget_values,
                widget_index,
                input_type,
                input_name
            )

            if match_result:
                inputs[input_name] = match_result['value']
                widget_index = match_result['next_index']
            else:
                self.logger.warning(
                    f"No widget value found for input '{input_name}' "
                    f"(type: {input_type}, index: {widget_index})"
                )

        return inputs

    def _find_next_compatible_widget(
        self,
        widget_values: List[Any],
        start_index: int,
        expected_type: str,
        input_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the next widget value that matches the expected type.

        Args:
            widget_values: List of widget values
            start_index: Index to start searching from
            expected_type: Expected ComfyUI type (INT, FLOAT, STRING, etc.)
            input_name: Name of the input (for logging)

        Returns:
            Dict with 'value' and 'next_index', or None if not found
        """
        # First pass: try to find type-compatible value
        for i in range(start_index, len(widget_values)):
            widget_value = widget_values[i]

            if self._check_type_compatibility(widget_value, expected_type):
                self.logger.debug(
                    f"Matched widget value {widget_value} to input '{input_name}' "
                    f"(type: {expected_type})"
                )
                return {
                    'value': widget_value,
                    'next_index': i + 1
                }

        # Second pass: fallback to next available value if any
        if start_index < len(widget_values):
            self.logger.warning(
                f"No type match for '{input_name}' (expected {expected_type}), "
                f"using next value anyway: {widget_values[start_index]}"
            )
            return {
                'value': widget_values[start_index],
                'next_index': start_index + 1
            }

        # No values left
        return None

    def _check_type_compatibility(self, value: Any, expected_type: str) -> bool:
        """
        Check if a widget value matches the expected input type.

        Args:
            value: The widget value to check
            expected_type: The expected ComfyUI type (INT, FLOAT, STRING, COMBO, etc.)

        Returns:
            True if the value type is compatible with the expected type
        """
        if expected_type == 'INT':
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == 'FLOAT':
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type in ('STRING', 'COMBO'):
            return isinstance(value, str)
        elif expected_type == 'BOOLEAN':
            return isinstance(value, bool)
        else:
            # For unknown types, accept anything
            return True

    def _extract_input_nodes(self) -> None:
        """
        Extract nodes with 'INPUT_' prefix from workflow.

        INPUT_ nodes are special nodes in ComfyUI workflows that represent
        parameters that should be exposed to the user. They're identified
        by having a title that starts with "INPUT_".
        """
        self.input_nodes = {}

        if not self.workflow_data:
            return

        for node_id, node_data in self.workflow_data.items():
            try:
                # Skip if node_data is not a dict (malformed workflow data)
                if not isinstance(node_data, dict):
                    self.logger.warning(
                        f"Skipping non-dict node {node_id}: {type(node_data).__name__}"
                    )
                    continue

                class_type = node_data.get('class_type', '')
                title = node_data.get('_meta', {}).get('title', '')

            except Exception as e:
                self.logger.error(f"Failed processing node {node_id}: {e}")
                self.logger.debug(f"Node data: {node_data}")
                import traceback
                traceback.print_exc()
                continue

            # Check if this is an input node (title starts with INPUT_)
            if title.startswith('INPUT_'):
                input_name = title[6:]  # Remove 'INPUT_' prefix
                self.input_nodes[node_id] = {
                    'name': input_name,
                    'class_type': class_type,
                    'inputs': node_data.get('inputs', {}),
                    'node_data': node_data
                }
                self.logger.debug(
                    f"Found INPUT_ node: {input_name} (type: {class_type}, id: {node_id})"
                )

        self.logger.info(f"Extracted {len(self.input_nodes)} INPUT_ nodes")

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

        print(f"[UPDATE DEBUG] Input nodes to update: {list(self.input_nodes.keys())}")
        print(f"[UPDATE DEBUG] Input values: {input_values}")

        # Create a deep copy to avoid modifying original
        try:
            updated_workflow = json.loads(json.dumps(self.workflow_data))
            print(f"[UPDATE DEBUG] Workflow copied successfully, {len(updated_workflow)} nodes")
        except Exception as e:
            print(f"[UPDATE ERROR] Failed to copy workflow: {e}")
            raise

        for node_id, node_info in self.input_nodes.items():
            try:
                param_name = node_info['name']
                sanitized_name = self._sanitize_name(param_name)
                print(f"[UPDATE DEBUG] Processing node {node_id}, param: {sanitized_name}")

                if sanitized_name in input_values:
                    new_value = input_values[sanitized_name]
                    print(f"[UPDATE DEBUG] Updating {node_id} with value: {new_value}")

                    # Update the node's inputs with new value
                    if node_id in updated_workflow:
                        node_data = updated_workflow[node_id]
                        print(f"[UPDATE DEBUG] Node {node_id} type: {type(node_data).__name__}")

                        # Skip if node_data is not a dict (malformed workflow)
                        if not isinstance(node_data, dict):
                            print(f"[UPDATE WARNING] Node {node_id} is not a dict: {node_data}")
                            continue

                        self._update_node_value(
                            node_data,
                            new_value,
                            node_info['class_type']
                        )
                        print(f"[UPDATE DEBUG] Successfully updated node {node_id}")
                    else:
                        print(f"[UPDATE WARNING] Node {node_id} not found in workflow")

            except Exception as e:
                print(f"[UPDATE ERROR] Failed updating node {node_id}: {e}")
                print(f"[UPDATE ERROR] Node info: {node_info}")
                import traceback
                traceback.print_exc()
                continue

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
