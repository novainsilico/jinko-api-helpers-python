from unittest.mock import patch, MagicMock
import unittest
import jinko_helpers as jinko
import pandas as pd


class TestCheckTrialStatus(unittest.TestCase):
    @patch("jinko_helpers.makeRequest")
    def test_check_trial_status_completed(self, mock_makeRequest):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "isRunning": False,
            "perArmSummary": {
                "arm1": {"countPending": 0, "countError": 1, "countSuccess": 3},
                "arm2": {"countPending": 0, "countError": 0, "countSuccess": 4},
            },
        }
        mock_makeRequest.return_value = mock_response
        status_summary = jinko.monitor_trial_until_completion(
            "trial_core_item_id", "trial_snapshot_id"
        )
        # Assert that the DataFrame was created correctly
        expected_df = pd.DataFrame(
            {
                "Arm": ["arm1", "arm2"],
                "countPending": [0, 0],
                "countError": [1, 0],
                "countSuccess": [3, 4],
            }
        )
        pd.testing.assert_frame_equal(status_summary, expected_df)

    @patch("jinko_helpers.makeRequest")
    def test_is_trial_completed(self, mock_makeRequest):
        mock_response = MagicMock()
        mock_response.json.return_value = {"isRunning": False}
        mock_makeRequest.return_value = mock_response
        is_trial_running = jinko.is_trial_running(
            "trial_core_item_id", "trial_snapshot_id"
        )
        self.assertEqual(is_trial_running, False)


if __name__ == "__main__":
    unittest.main()
