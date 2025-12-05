"""
Unit tests for ComfyUI Workflow Parser
"""

import unittest
import json
import sys
import os
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from comfy_bridge import ComfyWorkflowParser


class TestComfyWorkflowParser(unittest.TestCase):
    """Test cases for ComfyWorkflowParser class."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample workflow with INPUT nodes
        self.sample_workflow = {
            "1": {
                "inputs": {
                    "text": "a beautiful landscape"
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "INPUT_positive_prompt"
                }
            },
            "2": {
                "inputs": {
                    "text": "ugly, blurry"
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "INPUT_negative_prompt"
                }
            },
            "3": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {
                    "title": "INPUT_dimensions"
                }
            },
            "4": {
                "inputs": {
                    "ckpt_name": "model.safetensors"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {
                    "title": "Load Checkpoint"
                }
            }
        }

    def test_initialization_no_file(self):
        """Test parser initialization without file."""
        parser = ComfyWorkflowParser()
        self.assertIsNone(parser.workflow_path)
        self.assertIsNone(parser.workflow_data)
        self.assertEqual(parser.input_nodes, {})

    def test_load_workflow_from_string(self):
        """Test loading workflow from JSON string."""
        parser = ComfyWorkflowParser()
        workflow_json = json.dumps(self.sample_workflow)

        result = parser.load_workflow_from_string(workflow_json)

        self.assertEqual(result, self.sample_workflow)
        self.assertEqual(parser.workflow_data, self.sample_workflow)

    def test_extract_input_nodes(self):
        """Test extraction of INPUT nodes."""
        parser = ComfyWorkflowParser()
        parser.load_workflow_from_string(json.dumps(self.sample_workflow))

        input_nodes = parser.get_input_nodes()

        # Should have 3 INPUT nodes
        self.assertEqual(len(input_nodes), 3)

        # Check node names
        node_names = [node['name'] for node in input_nodes.values()]
        self.assertIn('positive_prompt', node_names)
        self.assertIn('negative_prompt', node_names)
        self.assertIn('dimensions', node_names)

    def test_no_input_nodes(self):
        """Test workflow with no INPUT nodes."""
        workflow = {
            "1": {
                "inputs": {"text": "test"},
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "Normal Node"}
            }
        }

        parser = ComfyWorkflowParser()
        parser.load_workflow_from_string(json.dumps(workflow))

        input_nodes = parser.get_input_nodes()
        self.assertEqual(len(input_nodes), 0)

    def test_get_input_parameters(self):
        """Test parameter definition generation."""
        parser = ComfyWorkflowParser()
        parser.load_workflow_from_string(json.dumps(self.sample_workflow))

        params = parser.get_input_parameters()

        # Should have 3 parameters
        self.assertEqual(len(params), 3)

        # Check parameter structure
        for param in params:
            self.assertIn('name', param)
            self.assertIn('label', param)
            self.assertIn('node_id', param)
            self.assertIn('class_type', param)
            self.assertIn('type', param)
            self.assertIn('parm_type', param)

    def test_sanitize_name(self):
        """Test name sanitization."""
        parser = ComfyWorkflowParser()

        # Test various inputs
        self.assertEqual(parser._sanitize_name("Simple Name"), "simple_name")
        self.assertEqual(parser._sanitize_name("Name-With-Dashes"), "name_with_dashes")
        self.assertEqual(parser._sanitize_name("Name__With__Multiple"), "name_with_multiple")
        self.assertEqual(parser._sanitize_name("  Leading  "), "leading")
        self.assertEqual(parser._sanitize_name("CamelCase"), "camelcase")

    def test_parameter_type_inference(self):
        """Test parameter type inference from class types."""
        parser = ComfyWorkflowParser()
        parser.load_workflow_from_string(json.dumps(self.sample_workflow))

        params = parser.get_input_parameters()

        # Find specific parameters
        positive_prompt = next(p for p in params if p['name'] == 'positive_prompt')
        dimensions = next(p for p in params if p['name'] == 'dimensions')

        # Check types
        self.assertEqual(positive_prompt['parm_type'], 'string')
        self.assertEqual(dimensions['parm_type'], 'intvector2')

    def test_update_workflow_inputs(self):
        """Test updating workflow with new input values."""
        parser = ComfyWorkflowParser()
        parser.load_workflow_from_string(json.dumps(self.sample_workflow))

        # Update values
        new_values = {
            'positive_prompt': 'new prompt text',
            'dimensions': [1024, 1024]
        }

        updated_workflow = parser.update_workflow_inputs(new_values)

        # Check updates
        self.assertEqual(
            updated_workflow['1']['inputs']['text'],
            'new prompt text'
        )
        self.assertEqual(
            updated_workflow['3']['inputs']['width'],
            1024
        )
        self.assertEqual(
            updated_workflow['3']['inputs']['height'],
            1024
        )

    def test_load_workflow_from_file(self):
        """Test loading workflow from file."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_workflow, f)
            temp_path = f.name

        try:
            parser = ComfyWorkflowParser(temp_path)

            self.assertEqual(parser.workflow_path, temp_path)
            self.assertEqual(parser.workflow_data, self.sample_workflow)
            self.assertIsNotNone(parser.cached_workflow)

        finally:
            os.unlink(temp_path)

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file raises error."""
        with self.assertRaises(FileNotFoundError):
            ComfyWorkflowParser('/nonexistent/file.json')

    def test_get_workflow_copy(self):
        """Test getting workflow copy."""
        parser = ComfyWorkflowParser()
        parser.load_workflow_from_string(json.dumps(self.sample_workflow))

        copy = parser.get_workflow_copy()

        # Modify copy
        copy['1']['inputs']['text'] = 'modified'

        # Original should be unchanged
        self.assertEqual(
            parser.workflow_data['1']['inputs']['text'],
            'a beautiful landscape'
        )

    def test_cached_workflow(self):
        """Test cached workflow preservation."""
        parser = ComfyWorkflowParser()
        parser.load_workflow_from_string(json.dumps(self.sample_workflow))

        # Update workflow
        parser.update_workflow_inputs({'positive_prompt': 'updated'})

        # Cached should still have original
        cached = parser.get_cached_workflow()
        self.assertEqual(
            cached['1']['inputs']['text'],
            'a beautiful landscape'
        )


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestComfyWorkflowParser)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
