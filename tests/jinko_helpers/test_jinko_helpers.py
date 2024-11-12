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
    def test_absolute_url_from_path(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        jinko_helpers.makeRequest(
            "/test-path",
        )
        (_, url), kwargs = mock_request.call_args
        self.assertEqual(url, "https://api.jinko.ai/test-path")

    @patch("requests.request")
    def test_make_request_get(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        response = jinko_helpers.makeRequest("/test-path", method="GET")
        self.assertEqual(response.json(), {"key": "value"})

    @patch("requests.request")
    def test_make_request_query_parameters(self, mock_request):
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        jinko_helpers.makeRequest(
            "/test-path?key=value1", method="GET", params={"key": ["value2", "value3"]}
        )
        _, kwargs = mock_request.call_args
        self.assertTrue("params" in kwargs)
        self.assertEqual(kwargs["params"], {"key": ["value2", "value3"]})

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

        jinko_helpers.makeRequest("/test-path", method="POST", csv_data="")
        _, kwargs = mock_request.call_args
        self.assertTrue("data" in kwargs)
        self.assertEqual(kwargs["headers"]["Content-Type"], "text/csv")
        self.assertFalse("Accept" in kwargs["headers"])

    @patch("requests.request")
    def test_make_request_post_raw(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        jinko_helpers.makeRequest(
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

        jinko_helpers.makeRequest(
            "/test-path",
            method="GET",
            data="",
            options={"output_format": "application/xml"},
        )
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["headers"]["Accept"], "application/xml")

    @patch("requests.request")
    def test_project_item_options(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        options = {
            "name": "TestName",
            "description": "TestDescription",
            "folder_id": "12345",
            "version_name": "v1.0",
        }
        jinko_helpers.makeRequest(
            "/test-path",
            method="GET",
            options=options,
        )

        _, kwargs = mock_request.call_args
        self.assertTrue("X-jinko-project-item-name" in kwargs["headers"])
        self.assertTrue("X-jinko-project-item-description" in kwargs["headers"])
        self.assertTrue("X-jinko-project-item-folder-ids" in kwargs["headers"])
        self.assertTrue("X-jinko-project-item-version-name" in kwargs["headers"])


if __name__ == "__main__":
    unittest.main()
