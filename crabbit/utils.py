"""Utility functions used in the crabbit package."""

__all__ = [
    "bold_text",
    "clear_directory",
    "merge_vpops",
    "merge_vpop_designs",
    "merge_csv",
]

import shutil
import os
import csv
import json
from typing import List, Generator

import jinko_helpers as jinko
from jinko_helpers.types import asDict as jinko_types


def bold_text(text: str) -> str:
    """Return bold text to print in console application."""
    return "\033[1m" + text + "\033[0m"


def clear_directory(directory: str, force: bool) -> None:
    """Remove files and folders, so that the directory becomes empty (except for hidden files)."""
    if not os.path.exists(directory):
        print("(The folder does not exist; it will be created.)")
        os.makedirs(directory, exist_ok=True)
        return True

    old_files = []
    old_dirs = []
    try:
        with os.scandir(directory) as it:
            for entry in it:
                if not entry.name.startswith(".") and entry.is_file():
                    old_files.append(entry)
                elif entry.is_dir():
                    old_dirs.append(entry)
    except NotADirectoryError:
        print("Error: the output path is not a folder")
        return False
    if not old_files and not old_dirs:
        return True

    max_tries = 5
    k = 0
    while k < max_tries:
        answer = "y"
        if not force:
            print(
                "Folder already exists! Do you want to clean it up (existing content will be removed)? (y/n)",
                end=" ",
            )
            answer = input()
        if answer == "n":
            return False
        elif answer == "y":
            try:
                for entry in old_files:
                    os.remove(entry)
                for entry in old_dirs:
                    shutil.rmtree(entry)
            except:
                print(
                    "Something wrong happened when cleaning the folder (maybe some files are locked by other application?)!"
                )
                return False
            return True
        k += 1
    return False


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
            print("The VpopDesign file is not valid!")
            return
    for required_key in [
        "marginalDistributions",
        "marginalCategoricals",
        "correlations",
    ]:
        if required_key not in vpop_design_data:
            print("The VpopDesign file is not valid!")
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
            yield os.path.split(item_path)[1], True, item_path
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
    return {"patients": total_patients}  # arbitrary


def merge_vpop_designs(
    vpop_designs_to_merge: List[str],
) -> jinko_types.VpopDesignWithModel | None:
    """
    Merge a stream of vpop designs into one, concatenating the marginals and correlations.
    When VpopDesigns are attached to different models/versions, the LAST ONE in the list is kept.
    Note: the resulting VpopDesign can become incompatible with the CM.
    """
    model_id = {}
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
        model_id = vpop_design_content["computationalModelId"]

        for item in vpop_design_content["correlations"]:
            x, y = sorted([item["x"], item["y"]])
            if (x, y) in correlations:
                print(
                    bold_text("\nError:"),
                    f"Duplicated correlation entry found between {x} and {y}\n",
                )
                return
            correlations[x, y] = item
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
        "computationalModelId": model_id,
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
