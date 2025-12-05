"""
Unit tests for ComfyUI API layer
"""

import unittest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from comfy_bridge import ComfyAPI


class TestComfyAPI(unittest.TestCase):
    """Test cases for ComfyAPI class."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = ComfyAPI(host='127.0.0.1', port=8188)

    def test_initialization(self):
        """Test API client initialization."""
        self.assertEqual(self.api.host, '127.0.0.1')
        self.assertEqual(self.api.port, 8188)
        self.assertEqual(self.api.base_url, 'http://127.0.0.1:8188')
        self.assertIsNotNone(self.api.client_id)

    def test_custom_host_port(self):
        """Test custom host and port."""
        api = ComfyAPI(host='192.168.1.100', port=9000)
        self.assertEqual(api.base_url, 'http://192.168.1.100:9000')

    def test_is_server_alive_unreachable(self):
        """Test server health check with unreachable server."""
        # Use invalid port to ensure failure
        api = ComfyAPI(host='127.0.0.1', port=99999)
        self.assertFalse(api.is_server_alive())

    def test_client_id_uniqueness(self):
        """Test that each API instance gets unique client ID."""
        api1 = ComfyAPI()
        api2 = ComfyAPI()
        self.assertNotEqual(api1.client_id, api2.client_id)

    # Note: The following tests require a running ComfyUI server
    # Uncomment and run when ComfyUI is available

    # def test_is_server_alive_reachable(self):
    #     """Test server health check with running server."""
    #     if self.api.is_server_alive():
    #         self.assertTrue(True)
    #     else:
    #         self.skipTest("ComfyUI server not running")

    # def test_get_queue_info(self):
    #     """Test getting queue information."""
    #     if not self.api.is_server_alive():
    #         self.skipTest("ComfyUI server not running")
    #
    #     queue_info = self.api.get_queue_info()
    #     self.assertIn('queue_running', queue_info)
    #     self.assertIn('queue_pending', queue_info)

    # def test_upload_image(self):
    #     """Test image upload."""
    #     if not self.api.is_server_alive():
    #         self.skipTest("ComfyUI server not running")
    #
    #     # Create a minimal PNG image (1x1 red pixel)
    #     png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    #
    #     result = self.api.upload_image(png_data, 'test.png')
    #     self.assertIn('name', result)


class TestComfyAPIIntegration(unittest.TestCase):
    """Integration tests requiring running ComfyUI server."""

    @classmethod
    def setUpClass(cls):
        """Check if ComfyUI server is available."""
        cls.api = ComfyAPI()
        cls.server_available = cls.api.is_server_alive()

        if not cls.server_available:
            print("\n⚠️  Warning: ComfyUI server not running at http://127.0.0.1:8188")
            print("   Integration tests will be skipped.")
            print("   Start ComfyUI to run full test suite.\n")

    def test_connection(self):
        """Test basic connection to ComfyUI."""
        if not self.server_available:
            self.skipTest("ComfyUI server not available")

        self.assertTrue(self.api.is_server_alive())
        print("✓ Successfully connected to ComfyUI server")


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestComfyAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestComfyAPIIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
