import unittest
from unittest.mock import patch, mock_open, MagicMock
import jinko_helpers as jinko
import json


class TestDownloadModel(unittest.TestCase):
    @patch("jinko_helpers.get_project_item_new")
    @patch("jinko_helpers.make_request")
    @patch(
        "os.path.join",
        return_value="/fake/path/ComputationalModel_Model_A_revision_1_label_v1.json",
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_download_model(
        self, mock_file, mock_path_join, mock_make_request, mock_get_project_item_new
    ):
        # Mock the response for `get_project_item_new`
        mock_get_project_item_new.return_value = {
            "sid": "example-sid",
            "coreId": {"id": "example-core-item-id"
                       , "snapshotId": "example-snapshot-id"},
            "type": "ComputationalModel",
            "name": "Model A",
            "version": {"revision": 1, "label": "v1"},
        }

        # Expected JSON response from the `make_request` mock
        expected_json_response = {
            "model": {
                "compartments": [
                    {
                        "_Iname": "Blood",
                        "_Iunit": "L",
                        "_Ivalue": {"contents": 1, "tag": "Const"},
                    }
                ]
            },
            "solvingOptions": None,
        }

        # Mock the response for `make_request`
        mock_make_request.return_value = MagicMock(json=lambda: expected_json_response)

        # Call the function with a file-saving path
        downloaded_model = jinko.download_model(
            model_core_item_id="example-core-id",
            model_snapshot_id="example-snapshot-id",
            file_path_for_saving="/fake/path",
        )

        # Assertions
        self.assertEqual(downloaded_model, expected_json_response)

        # Assert the file name was constructed correctly
        mock_path_join.assert_called_once_with(
            "/fake/path", "ComputationalModel_Model_A_revision_1_label_v1.json"
        )

        # Reconstruct the full content written to the file from multiple write calls
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)

        # Ensure the written content matches the expected JSON
        self.assertEqual(json.loads(written_content), expected_json_response)

    @patch("jinko_helpers.get_project_item_new")
    @patch("jinko_helpers.make_request")
    @patch(
        "os.path.join",
        return_value="/fake/path/ModelInterface_Model_A_revision_1_label_v1.json",
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_download_model_interface(
        self,
        mock_file,
        mock_path_join,
        mock_make_request,
        mock_get_project_item_new,
    ):

        # Mock the response for `get_project_item_new`
        mock_get_project_item_new.return_value = {
            "sid": "example-sid",
            "coreId": {"id": "example-core-item-id"
                       , "snapshotId": "example-snapshot-id"},
            "type": "ComputationalModel",
            "name": "Model A",
            "version": {"revision": 1, "label": "v1"},
        }

        # Mock the response from `download_model_or_model_interface`
        expected_interface_response = {
            "components": {
                "compartments": [
                    {
                        "id": "Blood",
                        "unit": "L",
                        "volume": 1,
                    }
                ]
            }
        }
        # Mock the response for `make_request`
        mock_make_request.return_value = MagicMock(
            json=lambda: expected_interface_response
        )

        # Call the function with arguments
        downloaded_interface = jinko.download_model_interface(
            model_core_item_id="example-core-id",
            model_snapshot_id="example-snapshot-id",
            file_path_for_saving="/fake/path",
        )

        # Assertions
        self.assertEqual(downloaded_interface, expected_interface_response)

        # Reconstruct the full content written to the file from multiple write calls
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)

        # Ensure the written content matches the expected JSON
        self.assertEqual(json.loads(written_content), expected_interface_response)

        # Assert the file path was constructed correctly
        mock_path_join.assert_called_once_with(
            "/fake/path", "ModelInterface_Model_A_revision_1_label_v1.json"
        )


if __name__ == "__main__":
    unittest.main()
