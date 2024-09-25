"""Module containing the command-line apps of crabbit."""

import os
import json
import zipfile
import io
import requests
import pandas as pd

import jinko_helpers as jinko
from crabbit.utils import get_calib_status, to_bold


class CrabbitDownloader:
    """Cli app for running the crabbit "download" mode"""

    def __init__(self, project_item, output_path):
        self.project_item = project_item
        self.output_path = output_path
        self.core_id = (
            self.project_item["coreId"] if "coreId" in self.project_item else ""
        )

    def run(self):
        if (
            not self.check_valid_item_type()
            or not self.check_calib_status()
            or not self.download_calib_inputs()
        ):
            return
        best_patient = self.find_best_calib_patient()
        if best_patient is None:
            return
        self.download_calib_patient_timeseries(best_patient)

    def check_valid_item_type(self):
        """Check whether the project item can be downloaded (currently only "Calibration" is supported) and get its CoreItemId."""
        if (
            "type" not in self.project_item
            or self.project_item["type"] != "Calibration"
            or not self.core_id
        ):
            print(
                'Currently "crabbit download" only supports the "Calibration" item type.'
            )
            return False
        print(
            to_bold(
                'Note: for the "Calibration" item type, only the results of the "best patient", i.e. highest optimizationWeightedScore, will be downloaded.'
            ),
            end="\n\n",
        )
        return True

    def check_calib_status(self):
        """Check whether the calibration can be downloaded depending on its status."""
        status = get_calib_status(self.core_id)
        if not status:
            return False
        elif status == "not_launched":
            print("Error: calibration is not launched! (is it the correct version?)")
            return False
        elif status != "completed":
            print("Warning: the status of the calibration is", status)
        return True

    def find_best_calib_patient(self):
        print("Finding the ID of the best calib patient...")
        response = jinko.makeRequest(
            path=f"/core/v2/result_manager/calibration/sorted_patients",
            method="POST",
            json={
                "calibId": {
                    "coreItemId": self.core_id["id"],
                    "snapshotId": self.core_id["snapshotId"],
                },
                "sortBy": "optimizationWeightedScore",
            },
        )
        if not response.json():
            print("Warning: best patient cannot be found! (is it the correct version?)")
            return None
        best_patient = response.json()[0]["patientNumber"]
        print("Best patient is", best_patient, end="\n\n")
        return best_patient

    def download_calib_inputs(self):
        """Download calibration inputs (currently only scorings and data tables are downloaded)."""
        csv_data = {}
        json_data = []
        try:
            response = jinko.makeRequest(
                path=f"/core/v2/calibration_manager/calibration/{self.core_id['id']}/snapshots/{self.core_id['snapshotId']}/bundle",
                method="GET",
            )
            archive = zipfile.ZipFile(io.BytesIO(response.content))
            for item in archive.namelist():
                if item.startswith("data_tables"):
                    if not item.endswith(".csv"):
                        continue
                    csv_data[item.split("/")[1]] = pd.read_csv(
                        io.StringIO(archive.read(item).decode("utf-8")), sep=","
                    )
                elif item.startswith("scorings"):
                    json_data.append(json.loads(archive.read(item).decode("utf-8")))
        except requests.exceptions.HTTPError:
            print(
                "Error: failed to download calibration inputs (scorings and data tables)."
            )
            return False
        if json_data:
            merged_json_scorings = {
                "objectives": sum((item["objectives"] for item in json_data), [])
            }
            if merged_json_scorings["objectives"]:
                json_path = os.path.join(self.output_path, "Scorings.json")
                json.dump(merged_json_scorings, open(json_path, "w", encoding="utf-8"))
        if csv_data:
            try:
                merged_csv_data = pd.concat(csv_data.values(), ignore_index=True)
                # when data tables can be merged, save them in one single file
                merged_csv_data.to_csv(
                    os.path.join(self.output_path, "ReferenceTimeSeries.csv"),
                    index=False,
                )
            except:
                # when data tables cannot be merged, save them in the original name
                for csv_name, csv_df in csv_data.items():
                    csv_df.to_csv(os.path.join(self.output_path, csv_name), index=False)
        assert (
            json_data or csv_data
        ), "Something wrong happened (calibration without scoring nor data table)."
        print("Downloaded calibration inputs (scorings and data tables).", end="\n\n")
        return True

    def download_calib_patient_timeseries(self, patient_name):
        print("Downloading the timeseries of the best calib patient...")
        pretty_patient_name = (
            "CalibratedPatient"  # nice name to be used in visualization
        )
        timeseries_path = os.path.join(self.output_path, "ModelResult")
        os.mkdir(timeseries_path)
        arms = []
        try:
            response = jinko.makeRequest(
                path=f"/core/v2/result_manager/calibration/model_result",
                method="POST",
                json={
                    "calibId": {
                        "coreItemId": self.core_id["id"],
                        "snapshotId": self.core_id["snapshotId"],
                    },
                    "patientId": patient_name,
                },
            )
            for arm_item in response.json():
                arm_name = arm_item["group"][0]["contents"]
                arms.append(arm_name)
                assert (
                    arm_item["indexes"]["patientNumber"] == patient_name
                ), "Something wrong happened (patient number mismatch between requests)!"
                result_path = os.path.join(
                    timeseries_path, f"{pretty_patient_name}_{arm_name}.json"
                )
                json.dump(
                    {"res": arm_item["res"]}, open(result_path, "w", encoding="utf-8")
                )
        except (requests.exceptions.HTTPError, TypeError, KeyError):
            print("Error: failed to download the timeseries.")
            return
        arm_count = len(arms)
        print(
            f'Successfully downloaded the timeseries of {arm_count} protocol arm{"s" if arm_count > 1 else ""}.',
            end="\n\n",
        )
