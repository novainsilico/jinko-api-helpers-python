import unittest
from unittest.mock import patch, MagicMock
import jinko_helpers


class TestJinkoHelpers(unittest.TestCase):

    @patch("requests.get")
    def test_check_authentication_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        self.assertTrue(jinko_helpers.checkAuthentication())

    @patch("requests.get")
    def test_check_authentication_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        self.assertFalse(jinko_helpers.checkAuthentication())

    @patch("requests.request")
    def test_make_request_get(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        response = jinko_helpers.makeRequest("/test-path", method="GET")
        self.assertEqual(response.json(), {"key": "value"})

    @patch("requests.request")
    def test_make_request_post_json(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        response = jinko_helpers.makeRequest(
            "/test-path", method="POST", json={"data": "test"}
        )
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertFalse("Accept" in kwargs["headers"])
        self.assertTrue("json" in kwargs)
        self.assertEqual(response.json(), {"key": "value"})

    @patch("requests.request")
    def test_make_request_post_csv(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        response = jinko_helpers.makeRequest("/test-path", method="POST", csv_data="")
        _, kwargs = mock_request.call_args
        self.assertTrue("data" in kwargs)
        self.assertEqual(kwargs["headers"]["Content-Type"], "text/csv")
        self.assertFalse("Accept" in kwargs["headers"])

    @patch("requests.request")
    def test_make_request_post_raw(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        response = jinko_helpers.makeRequest(
            "/test-path",
            method="POST",
            data="",
            options={"input_format": "application/xml"},
        )
        _, kwargs = mock_request.call_args
        self.assertTrue("data" in kwargs)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/xml")
        self.assertFalse("Accept" in kwargs["headers"])

    @patch("requests.request")
    def test_make_request_ask_custom_output_format(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        response = jinko_helpers.makeRequest(
            "/test-path",
            method="GET",
            data="",
            options={"output_format": "application/xml"},
        )
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["headers"]["Accept"], "application/xml")

    def test_encode_custom_headers(self):
        custom_headers = {
            "name": "TestName",
            "description": "TestDescription",
            "folder_id": "12345",
            "version_name": "v1.0",
        }
        encoded_headers = jinko_helpers.encodeCustomHeaders(custom_headers)

        self.assertIn("X-jinko-project-item-name", encoded_headers)
        self.assertIn("X-jinko-project-item-description", encoded_headers)
        self.assertIn("X-jinko-project-item-folder-ids", encoded_headers)
        self.assertIn("X-jinko-project-item-version-name", encoded_headers)

    def test_make_url(self):
        self.assertEqual(
            jinko_helpers.makeUrl("/test-path"), "https://api.jinko.ai/test-path"
        )


if __name__ == "__main__":
    unittest.main()
