"""Module containing the command-line apps of crabbit."""

__all__ = ["CrabbitDownloader", "CrabbitMerger"]

import os
import json
import zipfile
import io
import requests
import pandas as pd

import jinko_helpers as jinko
from crabbit.utils import (
    bold_text,
    merge_vpop_designs,
    merge_vpops,
    merge_csv,
)


class CrabbitDownloader:
    """CLI app for running the crabbit "download" mode."""

    def __init__(self, project_item, output_path):
        self.project_item = project_item
        self.output_path = output_path
        self.core_id_dict = self.project_item.get("coreId", {})

        self.pretty_patient_name = (
            "CalibratedPatient"  # nice name to be used in calibration visualization
        )

    def run(self):
        """Main function of the download app."""
        if not self.check_valid_item_type():
            return
        download_type = self.project_item["type"]

        if download_type == "Calibration":
            if not self.check_calib_status() or not self.download_scorings(calib=True):
                return
            best_patient = self.find_best_calib_patient()
            if best_patient is None:
                return
            self.download_calib_patient_timeseries(best_patient)
            self.download_calib_patient_scalar_results(best_patient)
            print(
                bold_text("Done!"),
                f"To visualize: dark-crabbit -- trialViz {self.output_path}",
            )

        elif download_type == "Trial":
            if not self.check_trial_status() or not self.check_trial_without_vpop():
                return
            self.download_scorings(calib=False)
            self.download_trial_without_vpop_timeseries()
            print(
                bold_text("Done!"),
                f"To visualize: dark-crabbit -- trialViz {self.output_path}",
            )

        elif download_type == "ComputationalModel":
            model = jinko.make_request(
                f"/core/v2/model_manager/jinko_model/{self.core_id_dict['id']}/snapshots/{self.core_id_dict['snapshotId']}"
            ).json()[
                "model"
            ]  # discard metadata and solving options
            version = self.project_item.get("version", {})
            if not version or not version["label"]:
                print(
                    bold_text("Error:"),
                    "Cannot download a Computational Model that is not a named version.",
                )
                return
            output_file = os.path.join(self.output_path, f'{version["label"]}.json')
            json.dump(model, open(output_file, "w", encoding="utf-8"), indent=4)
            print(bold_text("Done!"), f"Output file: {output_file}")

        else:  # placeholder for future download types
            pass

    def check_valid_item_type(self):
        """Check whether the project item can be downloaded (currently only "Calibration" or "ComputationalModel" is supported) and get its CoreItemId."""
        if (
            "type" not in self.project_item
            or self.project_item["type"]
            not in ["Calibration", "ComputationalModel", "Trial"]
            or not self.core_id_dict
        ):
            print(
                bold_text("Error:"),
                'Currently "crabbit download" only supports the "Calibration", "Trial" and "ComputationalModel" item types.',
            )
            return False
        # print an additional warning when using download on calibration
        if self.project_item["type"] == "Calibration":
            print(
                bold_text(
                    'Note: for the "Calibration" item type, only the results of the "best patient", i.e. highest optimizationWeightedScore, will be downloaded.'
                ),
                end="\n\n",
            )
        return True

    def check_calib_status(self):
        """Check whether the calibration can be downloaded depending on its status."""
        status = jinko.get_calib_status(self.core_id_dict)
        if not status:
            return False
        elif status == "not_launched":
            print("Error: calibration is not launched! (is it the correct version?)")
            return False
        elif status != "completed":
            print("Warning: the status of the calibration is", status)
        return True

    def check_trial_status(self):
        """Check whether the trial can be downloaded depending on its status."""
        is_completed = jinko.is_trial_completed(self.core_id_dict)
        if not is_completed:
            print("Error: trial is not completed! (is it the correct version?)")
            return False
        return True

    def check_trial_without_vpop(self):
        try:
            response = jinko.makeRequest(
                path=f"/core/v2/trial_manager/trial/{self.core_id_dict['id']}/snapshots/{self.core_id_dict['snapshotId']}",
                method="GET",
            )
            response_json = response.json()
            if "vpopId" in response_json:
                print(
                    bold_text("Error:"),
                    'Currently "crabbit download" only supports Trial without any vpop (single patient trial).',
                )
                return False
            return True
        except requests.exceptions.HTTPError:
            return False

    def find_best_calib_patient(self):
        """Return the "patientNumber" of the best calibration patient, i.e. highest optimizationWeightedScore."""
        print("Finding the ID of the best calib patient...")
        response = jinko.make_request(
            path=f"/core/v2/result_manager/calibration/sorted_patients",
            method="POST",
            json={
                "calibId": {
                    "coreItemId": self.core_id_dict["id"],
                    "snapshotId": self.core_id_dict["snapshotId"],
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

    def download_scorings(self, calib):
        """Download calibration/trial inputs (currently only scorings and data tables are downloaded)."""
        route = "calibration_manager/calibration" if calib else "trial_manager/trial"
        pretty_name = "calibration" if calib else "trial"
        csv_data = {}
        json_data = []
        try:
            response = jinko.make_request(
                path=f"/core/v2/{route}/{self.core_id_dict['id']}/snapshots/{self.core_id_dict['snapshotId']}/bundle",
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
                f"Error: failed to download {pretty_name} inputs (scorings and data tables)."
            )
            return False
        if calib:
            assert (
                json_data or csv_data
            ), "Something wrong happened (calibration without scoring nor data table)."
        if json_data:
            merged_json_scorings = {
                "objectives": sum(
                    (
                        (item["objectives"] for item in json_data)
                        if "objectives" in item
                        else []
                    ),
                    [],
                )
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
                try:
                    # trim the data tables to the minimum columns then try merge again
                    trimmed_csv = []
                    mandatory_columns = [
                        "armScope",
                        "obsId",
                        "time",
                        "value",
                        "narrowRangeLowBound",
                        "narrowRangeHighBound",
                        "wideRangeLowBound",
                        "wideRangeHighBound",
                    ]
                    for csv_name, csv_df in csv_data.items():
                        data_table_id = csv_name.split(".csv")[0]
                        sub_csv_df = csv_df.loc[:, mandatory_columns]
                        sub_csv_df["dataTableID"] = data_table_id
                        trimmed_csv.append(sub_csv_df)
                    merged_csv_data = pd.concat(trimmed_csv, ignore_index=True)
                    # when data tables can be merged, save them in one single file
                    merged_csv_data.to_csv(
                        os.path.join(self.output_path, "ReferenceTimeSeries.csv"),
                        index=False,
                    )
                except:
                    # if still cannot merge, save the data table separately
                    for csv_name, csv_df in csv_data.items():
                        csv_df.to_csv(
                            os.path.join(self.output_path, csv_name), index=False
                        )
        print(
            f"Downloaded {pretty_name} inputs (scorings and data tables).", end="\n\n"
        )
        return True

    def download_calib_patient_timeseries(self, patient_id):
        """Download one calibration patient's timeseries."""
        print("Downloading the timeseries of the best calib patient...")
        timeseries_path = os.path.join(self.output_path, "ModelResult")
        os.mkdir(timeseries_path)
        arms = []
        try:
            response = jinko.make_request(
                path=f"/core/v2/calibration_manager/calibration/{self.core_id_dict['id']}/snapshots/{self.core_id_dict['snapshotId']}/results_summary",
                method="GET",
            )
            ts_ids = [item["id"] for item in response.json()["timeseries"]]
            if "Time" not in ts_ids:
                print("Error: failed to download the timeseries.")
                return
            response = jinko.make_request(
                path=f"/core/v2/result_manager/calibration/model_result",
                method="POST",
                json={
                    "calibId": {
                        "coreItemId": self.core_id_dict["id"],
                        "snapshotId": self.core_id_dict["snapshotId"],
                    },
                    "patientId": patient_id,
                    "select": ts_ids,
                },
            )
            for arm_item in response.json():
                arm_name = arm_item["indexes"]["scenarioArm"]
                arms.append(arm_name)
                assert (
                    arm_item["indexes"]["patientNumber"] == patient_id
                ), "Something wrong happened (patient number mismatch between requests)!"
                result_path = os.path.join(
                    timeseries_path, f"{self.pretty_patient_name}_{arm_name}.json"
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

    def download_trial_without_vpop_timeseries(self):
        """Download the no-vpop-trial patient's timeseries."""
        print("Downloading the timeseries of the trial patient...")
        timeseries_path = os.path.join(self.output_path, "ModelResult.zip")
        try:
            response = jinko.make_request(
                path=f"/core/v2/trial_manager/trial/{self.core_id_dict['id']}/snapshots/{self.core_id_dict['snapshotId']}/output_ids",
                method="GET",
            )
            ts_ids = [item["id"] for item in response.json()]
            response = jinko.make_request(
                path=f"/core/v2/result_manager/timeseries_summary",
                method="POST",
                json={
                    "select": ts_ids,
                    "trialId": {
                        "coreItemId": self.core_id_dict["id"],
                        "snapshotId": self.core_id_dict["snapshotId"],
                    },
                },
            )
            with open(timeseries_path, "wb") as output_file:
                output_file.write(response.content)
        except (requests.exceptions.HTTPError, IndexError, KeyError):
            print("Error: failed to download the timeseries.")
            return
        print(
            f"Successfully downloaded the timeseries.",
            end="\n\n",
        )

    def download_calib_patient_scalar_results(self, patient_id):
        """Download one calibration patient's scalar results (into scalar arrays, categorical arrays and scalar metadata)."""
        print("Downloading the scalar results of the best calib patient...")
        scalar_array_path = os.path.join(self.output_path, "ScalarArrays")
        categorical_array_path = os.path.join(self.output_path, "CategoricalArrays")
        metadata_path = os.path.join(self.output_path, "ScalarMetaData.json")
        os.mkdir(scalar_array_path)
        os.mkdir(categorical_array_path)
        scalars, categoricals, scalars_cross, categoricals_cross = {}, {}, {}, {}
        arms = set()
        try:
            response = jinko.make_request(
                path=f"/core/v2/result_manager/calibration/scalar_result",
                method="POST",
                json={
                    "calibId": {
                        "coreItemId": self.core_id_dict["id"],
                        "snapshotId": self.core_id_dict["snapshotId"],
                    },
                    "patientId": patient_id,
                },
            )
            response = response.json()
            for (
                response_subtype,
                multi_field,
                array_path,
                metadata_dict,
                cross_metadata_dict,
                has_unit,
            ) in zip(
                ["outputs", "outputsCategorical"],
                ["scalarValues", "categoricalLevels"],
                [scalar_array_path, categorical_array_path],
                [scalars, categoricals],
                [scalars_cross, categoricals_cross],
                [True, False],
            ):
                for arm_item in response[response_subtype]:
                    arm_name = arm_item["indexes"]["scenarioArm"]
                    is_cross = arm_name == "crossArms"
                    if not is_cross:
                        arms.add(arm_name)
                    assert (
                        arm_item["indexes"]["patientNumber"] == patient_id
                    ), "Something wrong happened (patient number mismatch between requests)!"
                    scalar_array = []
                    for one_scalar in arm_item["res"]:
                        # fetch scalar metadata
                        scalar_id = one_scalar["id"]
                        scalar_unit = (
                            one_scalar["unit"] if "unit" in one_scalar else None
                        )
                        if is_cross:
                            if scalar_id not in cross_metadata_dict:
                                cross_metadata_dict[scalar_id] = {
                                    "description": None,
                                    "id": scalar_id,
                                    "type": one_scalar["type"],
                                }
                                if has_unit:
                                    cross_metadata_dict[scalar_id]["unit"] = scalar_unit
                        else:
                            if scalar_id not in metadata_dict:
                                metadata_dict[scalar_id] = {
                                    "arms": set(),
                                    "description": None,
                                    "id": scalar_id,
                                    "type": one_scalar["type"],
                                }
                                if has_unit:
                                    metadata_dict[scalar_id]["unit"] = scalar_unit
                            metadata_dict[scalar_id]["arms"].add(arm_name)

                        # turn the scalar array record into multi-patient format
                        one_scalar[multi_field] = []
                        one_scalar["errors"] = []
                        if "value" in one_scalar:
                            one_scalar[multi_field] = [one_scalar["value"]]
                            del one_scalar["value"]
                        if "error" in one_scalar:
                            one_scalar["errors"] = [one_scalar["error"]]
                            del one_scalar["error"]
                        scalar_array.append(one_scalar)

                    # save the scalar array
                    result_path = os.path.join(array_path, f"{arm_name}.json")
                    json.dump(scalar_array, open(result_path, "w", encoding="utf-8"))

        except (requests.exceptions.HTTPError, TypeError, KeyError):
            print("Error: failed to download the scalar results.")
            return

        # save the scalar metadata
        metadata_json = {"arms": list(arms), "patients": [self.pretty_patient_name]}
        for metadata_dict, metadata_array in zip(
            [scalars, categoricals, scalars_cross, categoricals_cross],
            ["scalars", "categoricals", "scalarsCrossArm", "categoricalsCrossArm"],
        ):
            metadata_json[metadata_array] = []
            # flatten the metadata dict (scalarID-indexed) into array
            for scalar_id, one_scalar_metadata in metadata_dict.items():
                if "arms" in one_scalar_metadata:
                    one_scalar_metadata["arms"] = list(one_scalar_metadata["arms"])
                metadata_json[metadata_array].append(
                    {"id": scalar_id} | one_scalar_metadata
                )
        json.dump(metadata_json, open(metadata_path, "w", encoding="utf-8"))

        arm_count = len(arms)
        print(
            f'Successfully downloaded the scalar results of {arm_count} protocol arm{"s" if arm_count > 1 else ""}.',
            end="\n\n",
        )


class CrabbitMerger:
    """CLI app for running the crabbit "merge" mode."""

    CSV = ".csv"
    JSON = ".json"
    SUPPORTED_EXTS = (CSV, JSON)

    def __init__(self, input_paths, output_path):
        self.input_paths = input_paths
        self.output_path = output_path
        self.to_merge = []
        self.ext = None

    def run(self):
        """Main function of the merge app."""
        if not self.check_options():
            return
        if self.ext == self.CSV:
            self.merge_csv_()
            return
        if os.path.split(self.to_merge[0])[1].startswith("VpopDesign"):
            json_output = self.merge_vpop_designs_()
        else:
            json_output = self.merge_vpops_()
        if json_output is not None:
            json.dump(
                json_output, open(self.output_path, "w+", encoding="utf-8"), indent=4
            )
            print(
                bold_text("Done!"),
                "Output successfully saved to:",
                self.output_path,
                end="\n\n",
            )

    def check_options(self):
        """Check the validity of inputs/output paths"""
        exts = set()
        for name in self.input_paths:
            _, ext = os.path.splitext(name)
            exts.add(ext)
            if os.path.exists(name) and os.path.isfile(name):
                self.to_merge.append(name)

        if not self.to_merge:
            print(bold_text("Error:"), "No file is found\n")
            return False
        elif len(self.to_merge) == 1:
            print(
                bold_text("Error:"),
                "Only one file is found. At least two are required\n",
            )
            return False

        self.to_merge.sort()
        print(f"Found {len(self.to_merge)} files matching the pattern:")
        for name in self.to_merge:
            print("\t", name)
        print()

        if len(exts) != 1:
            print(
                bold_text("Error:"),
                "Only files of the same extension (JSON or CSV) are supported\n",
            )
            return False
        self.ext = list(exts).pop()
        if self.ext not in self.SUPPORTED_EXTS:
            print(
                bold_text("Error:"),
                "Only JSON (Patients/VpopDesign) and CSV files are supported\n",
            )
            return False
        if self.ext != os.path.splitext(self.output_path)[1]:
            print(
                bold_text("Error:"),
                f"Output file must use the same extension {self.ext}\n",
            )
            return False
        return True

    def merge_vpops_(self):
        """Merge Vpop from local files or jinko to a JSON"""
        merged_vpop = merge_vpops(self.to_merge)
        if merged_vpop is None:
            return
        print(f"Writing the output... (size = {len(merged_vpop['patients'])})")
        return merged_vpop

    def merge_designs_(self):
        """Merge VpopDesign from local files or jinko to a JSON"""
        merged_vpop_design = merge_vpop_designs(self.to_merge)
        if merged_vpop_design is None:
            return
        print(f"Writing the output...")
        return merged_vpop_design

    def merge_csv_(self):
        """CSV merging is a crabbit specific operation concatening scalar results for a merged vpop."""
        csv_rows = merge_csv()
        if csv_rows is None:
            return
        print("Writing the output...")
        with open(self.output_path, "w", encoding="utf-8") as output_file:
            for row in csv_rows:
                output_file.write(",".join(row))
                output_file.write("\r\n")
        print(
            bold_text("Done!"),
            "Output successfully saved to:",
            self.output_path,
            end="\n\n",
        )
