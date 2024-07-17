import unittest
from unittest.mock import patch, MagicMock
import jinko_helpers

class TestJinkoHelpers(unittest.TestCase):

    @patch('jinko_helpers._requests.get')
    def test_check_authentication_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        self.assertTrue(jinko_helpers.checkAuthentication())

    @patch('jinko_helpers._requests.get')
    def test_check_authentication_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        self.assertFalse(jinko_helpers.checkAuthentication())

    @patch('jinko_helpers._requests.request')
    def test_make_request_get(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response
        
        response = jinko_helpers.makeRequest('/test-path', method='GET')
        self.assertEqual(response.json(), {"key": "value"})

    @patch('jinko_helpers._requests.request')
    def test_make_request_post(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response
        
        response = jinko_helpers.makeRequest('/test-path', method='POST', json={"data": "test"})
        self.assertEqual(response.json(), {"key": "value"})
        
    def test_encode_custom_headers(self):
        custom_headers = {
            "name": "TestName",
            "description": "TestDescription",
            "folder_id": "12345",
            "version_name": "v1.0"
        }
        encoded_headers = jinko_helpers.encodeCustomHeaders(custom_headers)
        
        self.assertIn("X-jinko-project-item-name", encoded_headers)
        self.assertIn("X-jinko-project-item-description", encoded_headers)
        self.assertIn("X-jinko-project-item-folder-ids", encoded_headers)
        self.assertIn("X-jinko-project-item-version-name", encoded_headers)
    
    def test_make_url(self):
        self.assertEqual(jinko_helpers.makeUrl('/test-path'), 'https://api.jinko.ai/test-path')

if __name__ == '__main__':
    unittest.main()
