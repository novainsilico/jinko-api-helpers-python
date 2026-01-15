"""Module containing the "merge" app and utilities of crabbit."""

__all__ = ["CrabbitMerger"]

import os
import json
import csv
import json
from typing import List, Generator

import jinko_helpers as jinko
from jinko_helpers.types import asDict as jinko_types
from crabbit.utils import bold_text, parse_jsonc


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
        if "VpopDesign" in os.path.split(self.to_merge[0])[1]:
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

    def merge_vpop_designs_(self):
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


def get_vpop_content_local(vpop_path) -> jinko_types.Vpop | None:
    """Read the "JSON VPOP" from a local file. The local counterpart of jinko.vpop.get_vpop_content."""
    with open(vpop_path, "r", encoding="utf-8") as j:
        try:
            vpop_data = json.loads(str(j.read()))
        except json.decoder.JSONDecodeError:
            print("The Patients file is not valid!")
            return
    if "patients" not in vpop_data:
        print("The Patients file is not valid!")
        return
    return vpop_data


def get_vpop_design_content_local(
    vpop_design_path,
) -> jinko_types.VpopDesignWithModel | None:
    """
    Read the "JSON VpopDesign" from a local file. The local counterpart of jinko.vpop.get_vpop_design_content.
    Note that local file does not have "computationalModelId"
    """
    with open(vpop_design_path, "r", encoding="utf-8") as j:
        try:
            vpop_design_data = json.loads(str(j.read()))
        except json.decoder.JSONDecodeError:
            success, vpop_design_data = parse_jsonc(vpop_design_path)
            if not success:
                print(
                    bold_text("Error:"),
                    "The VpopDesign file is not valid!",
                    vpop_design_path,
                )
                return
    for required_key in [
        "marginalDistributions",
        "marginalCategoricals",
        "correlations",
    ]:
        if required_key not in vpop_design_data:
            print(
                bold_text("Error:"),
                "The VpopDesign file is not valid!",
                vpop_design_path,
            )
            return
    if "computationalModelId" not in vpop_design_data:
        vpop_design_data["computationalModelId"] = {}
    return vpop_design_data


def get_vpop_index_set(vpop_data: jinko_types.Vpop | None) -> set:
    """Get the set of patientIndex from a VPOP"""
    if vpop_data is None:
        return set()
    patient_index_set = set()
    for patient in vpop_data["patients"]:
        if "patientIndex" not in patient:
            print('The Patients file is not valid! ("patientIndex" not found)')
            return set()
        patient_index_set.add(patient["patientIndex"])
    if len(patient_index_set) != len(vpop_data["patients"]):
        print("The Patients file is not valid! (duplicated patient index)")
        return set()
    return patient_index_set


def stream_input_paths(item_paths: List[str]) -> Generator:
    """Stream a list of input items, given by either URL or file paths."""
    for item_path in item_paths:
        sid, _ = jinko.get_sid_revision_from_url(item_path)
        if sid is None:
            yield os.path.split(item_path)[1], True, os.path.abspath(
                os.path.expanduser(item_path)
            )
        else:
            yield sid, False, sid


def merge_vpops(vpops_to_merge: List[str]) -> jinko_types.Vpop | None:
    """Merge a stream of vpops into one vpop, concatenating the patients."""
    patient_ids = set()
    total_patients = []
    for vpop_short_name, is_local, vpop_path in stream_input_paths(vpops_to_merge):
        print("Loading", vpop_short_name, end=" ", flush=True)
        if is_local:
            vpop_content = get_vpop_content_local(vpop_path)
        else:
            vpop_content = jinko.get_vpop_content(vpop_path)
        if vpop_content is None:
            return
        patient_index_set = get_vpop_index_set(vpop_content)
        if patient_index_set.intersection(patient_ids):
            print(
                bold_text("\nError:"),
                "Patients files with duplicated patientIndex cannot be merged\n",
            )
            return
        patient_ids.update(patient_index_set)
        print(f"(size = {len(patient_index_set)})")
        total_patients.extend(vpop_content["patients"])
    return {"patients": total_patients}


def merge_vpop_designs(
    vpop_designs_to_merge: List[str],
) -> jinko_types.VpopDesignWithModel | None:
    """
    Merge a stream of vpop designs into one, concatenating the marginals and correlations.
    Note: the resulting VpopDesign is no longer associated with a CM.
    """
    marginals = {}
    correlations = {}
    categoricals = {}
    for _, is_local, vpop_design_path in stream_input_paths(vpop_designs_to_merge):
        if is_local:
            vpop_design_content = get_vpop_design_content_local(vpop_design_path)
        else:
            vpop_design_content = jinko.get_vpop_design_content(vpop_design_path)
        if vpop_design_content is None:
            return

        for item in vpop_design_content["correlations"]:
            x = item["x"]["id"] if isinstance(item["x"], dict) else item["x"]
            y = item["y"]["id"] if isinstance(item["y"], dict) else item["y"]
            x, y = sorted([x, y])
            if (x, y) in correlations:
                print(
                    bold_text("\nError:"),
                    f"Duplicated correlation entry found between {x} and {y}\n",
                )
                return
            correlations[x, y] = {
                "x": x,
                "y": y,
                "correlationCoefficient": item["correlationCoefficient"],
            }
        for item in vpop_design_content["marginalDistributions"]:
            if item["id"] in marginals:
                print(
                    bold_text("\nError:"),
                    f"Duplicated marginal distribution entry found for {item['id']}\n",
                )
                return
            marginals[item["id"]] = item
        for item in vpop_design_content["marginalCategoricals"]:
            if item["id"] in categoricals:
                print(
                    bold_text("\nError:"),
                    f"Duplicated marginal categorical entry found for {item['id']}\n",
                )
                return
            categoricals[item["id"]] = item
    return {
        "correlations": list(correlations.values()),
        "marginalDistributions": list(marginals.values()),
        "marginalCategoricals": list(categoricals.values()),
    }


def merge_csv(csv_to_merge: str) -> List[List[str]] | None:
    """Merge the CSV by concateating rows, corresponding to merged vpop trial results."""
    csv_rows = []
    csv_header = None
    index_column = None
    patient_indices = set()
    for i, csv_path in enumerate(csv_to_merge):
        print("Loading", os.path.split(csv_path)[1])
        with open(csv_path, "r", newline="", encoding="utf-8") as input_file:
            reader = csv.reader(input_file, delimiter=",")
            header = next(reader)
            for j, item in enumerate(header):
                if item == "patientIndex":
                    index_column = j
            if i == 0:
                csv_header = header
                csv_rows = [csv_header]
            else:
                if header != csv_header:
                    print(
                        bold_text("\nError:"),
                        "CSV files with mismatching headers cannot be merged\n",
                    )
                    return
            for row in reader:
                csv_rows.append(row)
                if index_column is not None:
                    patient_index = row[index_column]
                    if patient_index in patient_indices:
                        print(
                            bold_text("\nError:"),
                            "CSV files with duplicated patientIndex cannot be merged\n",
                        )
                        return
                    patient_indices.add(patient_index)
    return csv_rows
