import unittest
from unittest.mock import patch, MagicMock
import jinko_helpers


class TestJinkoHelpers(unittest.TestCase):

    @patch("requests.get")
    def test_check_authentication_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        self.assertTrue(jinko_helpers.check_authentication())

    @patch("requests.get")
    def test_check_authentication_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        self.assertFalse(jinko_helpers.check_authentication())

    @patch("requests.request")
    def test_absolute_url_from_path(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        jinko_helpers.make_request(
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

        response = jinko_helpers.make_request("/test-path", method="GET")
        self.assertEqual(response.json(), {"key": "value"})

    @patch("requests.request")
    def test_make_request_query_parameters(self, mock_request):
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        jinko_helpers.make_request(
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

        response = jinko_helpers.make_request(
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

        jinko_helpers.make_request("/test-path", method="POST", csv_data="")
        _, kwargs = mock_request.call_args
        self.assertTrue("data" in kwargs)
        self.assertEqual(kwargs["headers"]["Content-Type"], "text/csv")
        self.assertFalse("Accept" in kwargs["headers"])

    @patch("requests.request")
    def test_make_request_post_raw(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        jinko_helpers.make_request(
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

        jinko_helpers.make_request(
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

        options: jinko_helpers.MakeRequestOptions
        options = {
            "name": "TestName",
            "description": "TestDescription",
            "folder_id": "12345",
            "version_name": "v1.0",
        }
        jinko_helpers.make_request(
            "/test-path",
            method="GET",
            options=options,
        )

        _, kwargs = mock_request.call_args
        self.assertTrue("X-jinko-project-item-name" in kwargs["headers"])
        self.assertTrue("X-jinko-project-item-description" in kwargs["headers"])
        self.assertTrue("X-jinko-project-item-folder-ids" in kwargs["headers"])
        self.assertTrue("X-jinko-project-item-version-name" in kwargs["headers"])


class TestGetProjectItem(unittest.TestCase):
    @patch("requests.request")
    def test_get_project_item_with_sid(self, mock_request):
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sid": "example-sid",
            "coreId": "example-core-id",
            "type": "ComputationalModel",
            "name": "Model A",
            "version": {"revision": 1, "label": "v1"},
        }
        mock_request.return_value = mock_response

        # Call the function with SID
        result = jinko_helpers.get_project_item_new(sid="example-sid", revision=1)

        # Assertions
        self.assertEqual(result, mock_response.json())

    def test_get_project_item_with_missing_parameters(self):
        # Call the function without SID or CoreItemId and check for ValueError
        with self.assertRaises(ValueError) as context:
            jinko_helpers.get_project_item_new()
        self.assertEqual(
            str(context.exception), "You must provide either 'sid' or 'core_item_id'."
        )

    @patch("requests.request")
    def test_get_project_item_with_ambiguous_parameters(self, mock_request):
        # Mock the API responses for ambiguity
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "sid": "example-sid",
            "coreId": "example-core-id",
            "type": "ComputationalModel",
            "name": "Model A",
            "version": {"revision": 1, "label": "v1"},
        }

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "sid": "different-sid",
            "coreId": "different-core-id",
            "type": "ComputationalModel",
            "name": "Model B",
            "version": {"revision": 2, "label": "v2"},
        }

        mock_request.side_effect = [mock_response_1, mock_response_2]

        # Call the function with ambiguous parameters and check for Exception
        with self.assertRaises(Exception) as context:
            jinko_helpers.get_project_item_new(
                sid="example-sid", core_item_id="different-core-id"
            )

        self.assertEqual(
            str(context.exception),
            "Parameters are ambiguous: they do not point to the same project item.",
        )
        self.assertEqual(mock_request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
