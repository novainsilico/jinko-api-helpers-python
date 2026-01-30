from unittest.mock import patch, MagicMock
import unittest
import jinko_helpers as jinko
import pandas as pd
import io
import zipfile


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


class TestTrialResultsHelpers(unittest.TestCase):
    @patch("jinko_helpers.make_request")
    def test_get_filtered_patients(self, mock_make_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"patients": ["p1", "p2"]}
        mock_make_request.return_value = mock_response

        filter_scalars = [{"foo": "bar"}]
        patients = jinko.get_filtered_patients("core", "snap", filter_scalars)

        self.assertEqual(patients, ["p1", "p2"])

    @patch("jinko_helpers.make_request")
    def test_get_timeseries_as_dataframe(self, mock_make_request):
        df = pd.DataFrame(
            {
                "Patient Id": ["p1", "p2", "p3"],
                "Value": [10, 20, 30],
            }
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("data.csv", df.to_csv(index=False))
        mock_response = MagicMock()
        mock_response.content = buffer.getvalue()
        mock_make_request.return_value = mock_response

        result = jinko.get_timeseries_as_dataframe(
            "core", "snap", {"ts1": ["arm1"]}, ["p2"]
        )

        self.assertEqual(result["Patient Id"].tolist(), ["p2"])
        self.assertEqual(result["Value"].tolist(), [20])

    @patch("jinko_helpers.trial.get_trial_scalars_summary")
    @patch("jinko_helpers.make_request")
    def test_get_trial_scalars_with_filter_and_groups_as_dataframe(
        self, mock_make_request, mock_get_trial_scalars_summary
    ):
        mock_get_trial_scalars_summary.return_value = {
            "arms": ["armA", "armB"],
            "scalars": [{"id": "s1"}, {"id": "s2"}],
            "scalarsCrossArm": [],
            "categoricals": [],
            "categoricalsCrossArm": [],
        }
        response = MagicMock()
        response.json.return_value = {
            "scalars": [
                [
                    [{"tag": "ByArm", "contents": ["arm2"]}],
                    {
                        "armA": {
                            "s1": {
                                "unit": "dimensionless",
                                "values": [1.0, 2.0],
                            }
                        },
                        "armB": {
                            "s2": {
                                "unit": "dimensionless",
                                "values": [3.0, 4.0],
                            }
                        },
                    },
                ]
            ],
        }
        mock_make_request.return_value = response

        scalar_ids = ["s1", "s2"]
        filter_scalars = [{"foo": "bar"}]
        scalar_groups = [{"tag": "ByArm", "contents": ["arm2"]}]

        result = jinko.get_trial_scalars_with_filter_and_groups_as_dataframe(
            "core", "snap", scalar_ids, filter_scalars, scalar_groups
        )

        records = sorted(
            result.to_dict(orient="records"),
            key=lambda r: (r["armId"], r["scalarId"], r["value"]),
        )
        expected = [
            {
                "armId": "armA",
                "scalarId": "s1",
                "value": 1.0,
                "unit": "dimensionless",
                "group": [{"tag": "ByArm", "contents": ["arm2"]}],
            },
            {
                "armId": "armA",
                "scalarId": "s1",
                "value": 2.0,
                "unit": "dimensionless",
                "group": [{"tag": "ByArm", "contents": ["arm2"]}],
            },
            {
                "armId": "armB",
                "scalarId": "s2",
                "value": 3.0,
                "unit": "dimensionless",
                "group": [{"tag": "ByArm", "contents": ["arm2"]}],
            },
            {
                "armId": "armB",
                "scalarId": "s2",
                "value": 4.0,
                "unit": "dimensionless",
                "group": [{"tag": "ByArm", "contents": ["arm2"]}],
            },
        ]
        self.assertEqual(records, expected)

    @patch("jinko_helpers.trial.get_trial_scalars_summary")
    @patch("jinko_helpers.make_request")
    def test_get_trial_scalars_with_filter_and_groups_without_groups(
        self, mock_make_request, mock_get_trial_scalars_summary
    ):
        mock_get_trial_scalars_summary.return_value = {
            "arms": ["armA"],
            "scalars": [{"id": "s1"}],
            "scalarsCrossArm": [],
            "categoricals": [],
            "categoricalsCrossArm": [],
        }
        response = MagicMock()
        response.json.return_value = {
            "scalars": [
                [
                    [],
                    {
                        "armA": {
                            "s1": {
                                "unit": "dimensionless",
                                "values": [1.0],
                            }
                        }
                    },
                ]
            ],
        }
        mock_make_request.return_value = response

        result = jinko.get_trial_scalars_with_filter_and_groups_as_dataframe(
            "core", "snap", ["s1"]
        )

        self.assertEqual(
            result.to_dict(orient="records"),
            [
                {
                    "armId": "armA",
                    "scalarId": "s1",
                    "value": 1.0,
                    "unit": "dimensionless",
                    "group": None,
                }
            ],
        )
        _, kwargs = mock_make_request.call_args
        self.assertNotIn("group", kwargs["json"])


if __name__ == "__main__":
    unittest.main()
