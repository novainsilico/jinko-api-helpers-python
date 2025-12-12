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
        mock_response.status_code = 200
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

    @patch("requests.request")
    def test_make_request_retries_then_succeeds(self, mock_request):
        first = MagicMock(status_code=500, headers={}, json=lambda: {}, text="error")
        second = MagicMock(status_code=200, headers={}, json=lambda: {}, text="ok")
        mock_request.side_effect = [first, second]

        response = jinko_helpers.make_request(
            "/test-path", max_retries=1, backoff_base=0
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)


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
        result = jinko_helpers.get_project_item(sid="example-sid", revision=1)

        # Assertions
        self.assertEqual(result, mock_response.json())

    def test_get_project_item_with_missing_parameters(self):
        # Call the function without SID or CoreItemId and check for ValueError
        with self.assertRaises(ValueError) as context:
            jinko_helpers.get_project_item()
        self.assertEqual(
            str(context.exception), "You must provide either 'sid' or 'core_item_id'"
        )

    @patch("requests.request")
    def test_get_project_item_with_label(self, mock_request):
        # Mock the API responses for ambiguity
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "example-sid",
                "coreId": {
                    "id": "example-core-id",
                    "snapshotId": "example-snapshot-id",
                },
                "label": "v1",
            },
            {
                "id": "example-sid",
                "coreId": {
                    "id": "example-core-id",
                    "snapshotId": "example-snapshot-id",
                },
                "label": "v2",
            },
        ]
        mock_request.return_value = mock_response
        result = jinko_helpers.get_project_item(sid="example-sid", label="v1")

        self.assertEqual(result, mock_response.json()[0])


class TestGetSidRevisionFomUrl(unittest.TestCase):
    def test_get_sid_revision_from_url_normal(self):
        self.assertEqual(
            jinko_helpers.get_sid_revision_from_url(
                "https://jinko.ai/ca-foo-bar?revision=42"
            ),
            ("ca-foo-bar", 42),
        )

    def test_get_sid_revision_from_url_no_revision(self):
        self.assertEqual(
            jinko_helpers.get_sid_revision_from_url("https://jinko.ai/cm-baz-nix"),
            ("cm-baz-nix", None),
        )

    def test_get_sid_revision_from_url_bad_url(self):
        self.assertEqual(
            jinko_helpers.get_sid_revision_from_url("https://jinko.ai"), (None, None)
        )
        self.assertEqual(
            jinko_helpers.get_sid_revision_from_url("https://jinko.ai/one/two"),
            (None, None),
        )

    def test_get_sid_revision_from_url_localhost_url(self):
        self.assertEqual(
            jinko_helpers.get_sid_revision_from_url(
                "http://localhost:8000/cm-bla-bla?revision=1"
            ),
            ("cm-bla-bla", 1),
        )


if __name__ == "__main__":
    unittest.main()
