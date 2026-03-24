from unittest.mock import patch, MagicMock
import unittest
import jinko_helpers as jinko


class TestGetLatestCalibWithStatus(unittest.TestCase):
    @patch("jinko_helpers.make_request")
    @patch("jinko_helpers.getCoreItemId")
    def test_get_latest_calib_with_single_status_string(
        self, mock_get_core_item_id, mock_make_request
    ):
        mock_get_core_item_id.return_value = {"id": "core-calib-id"}
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "status": "completed",
                "simulationId": {
                    "coreItemId": "calib-core",
                    "snapshotId": "calib-snapshot",
                },
            }
        ]
        mock_make_request.return_value = mock_response

        result = jinko.get_latest_calib_with_status("ca-ldh6-ROIN", "completed")

        self.assertEqual(
            result,
            {"coreItemId": "calib-core", "snapshotId": "calib-snapshot"},
        )
        mock_make_request.assert_called_once_with(
            "/core/v2/calibration_manager/calibration/core-calib-id/status",
            params={"statuses": ["completed"]},
        )

    @patch("jinko_helpers.make_request")
    @patch("jinko_helpers.getCoreItemId")
    def test_get_latest_calib_with_multiple_statuses(
        self, mock_get_core_item_id, mock_make_request
    ):
        mock_get_core_item_id.return_value = {"id": "core-calib-id"}
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "status": "stopped",
                "simulationId": {
                    "coreItemId": "calib-core",
                    "snapshotId": "calib-snapshot",
                },
            }
        ]
        mock_make_request.return_value = mock_response

        result = jinko.get_latest_calib_with_status(
            "ca-ldh6-ROIN", ["completed", "stopped"]
        )

        self.assertEqual(
            result,
            {"coreItemId": "calib-core", "snapshotId": "calib-snapshot"},
        )
        mock_make_request.assert_called_once_with(
            "/core/v2/calibration_manager/calibration/core-calib-id/status",
            params={"statuses": ["completed", "stopped"]},
        )

    @patch("jinko_helpers.make_request")
    @patch("jinko_helpers.getCoreItemId")
    def test_get_latest_calib_with_status_raises_when_api_returns_no_match(
        self, mock_get_core_item_id, mock_make_request
    ):
        mock_get_core_item_id.return_value = {"id": "core-calib-id"}
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_make_request.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            jinko.get_latest_calib_with_status("ca-ldh6-ROIN", "completed")

        self.assertEqual(
            str(context.exception),
            "Found no calibration with status among ['completed']",
        )

    def test_get_latest_calib_with_status_rejects_empty_statuses(self):
        with self.assertRaises(ValueError) as context:
            jinko.get_latest_calib_with_status("ca-ldh6-ROIN", [])

        self.assertEqual(
            str(context.exception),
            "statuses must contain at least one status",
        )


if __name__ == "__main__":
    unittest.main()
