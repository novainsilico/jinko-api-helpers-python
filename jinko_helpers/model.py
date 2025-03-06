import os
import jinko_helpers as jinko
from typing import List, Any, Literal, Optional, Union, cast
import json


def download_model(
    model_core_item_id=None,
    model_snapshot_id=None,
    model_sid: Optional[str] = None,
    model_revision: Optional[int] = None,
    file_path_for_saving: Optional[str] = None,
):
    """
    Downloads a model from the Jinko platform and optionally saves it to a local file.

    Args:
        model_core_item_id (str, optional): The CoreItemId of the model. Defaults to None.
        model_snapshot_id (str, optional): The snapshotId of the model. Defaults to None.
        model_sid (str, optional): The SID of the model. Defaults to None.
        model_revision (int, optional): The revision of the model. Defaults to None.
        file_path_for_saving (str, optional): The path where the model should be saved. Defaults to None.

    Returns:
        dict: The model data.
    """
    model = download_model_or_model_interface(
        "ComputationalModel",
        model_core_item_id,
        model_snapshot_id,
        model_sid,
        model_revision,
        file_path_for_saving,
    )
    # Perform manual runtime validation since TypeDict is not supported by Pylance as a poor man type checker
    required_keys = {"model", "solvingOptions"}
    if not isinstance(model, dict) or not required_keys.issubset(model.keys()):
        raise TypeError(
            f"Expected return type 'ModelWithOptsWithMetadata', but got {type(model).__name__} with missing keys."
        )
    return model


def download_model_interface(
    model_core_item_id=None,
    model_snapshot_id=None,
    model_sid: Optional[str] = None,
    model_revision: Optional[int] = None,
    file_path_for_saving: Optional[str] = None,
):
    """
    Downloads a model interface version from the Jinko platform and optionally saves it to a local file.

    Args:
        model_core_item_id (str, optional): The CoreItemId of the model interface. Defaults to None.
        model_snapshot_id (str, optional): The snapshotId of the model interface. Defaults to None.
        model_sid (str, optional): The SID of the model interface. Defaults to None.
        model_revision (int, optional): The revision of the model interface. Defaults to None.
        file_path_for_saving (str, optional): The path where the model interface should be saved. Defaults to None.

    Returns:
        dict: The model interface.
    """
    model_interface = download_model_or_model_interface(
        "ModelInterface",
        model_core_item_id,
        model_snapshot_id,
        model_sid,
        model_revision,
        file_path_for_saving,
    )
    # poor man solution for type checking
    return model_interface


def download_model_or_model_interface(
    item_type: Literal["ComputationalModel", "ModelInterface"],
    model_core_item_id=None,
    model_snapshot_id=None,
    model_sid: Optional[str] = None,
    model_revision: Optional[int] = None,
    file_path_for_saving: Optional[str] = None,
):
    """
    Downloads a model or model interface from the Jinko platform and optionally saves it to a local file. To be used internally.

    Args:
        item_type (str): The type of the item to download. Must be either "model" or "model_interface".
        model_core_item_id (str, optional): The CoreItemId of the model or model interface. Defaults to None.
        model_snapshot_id (str, optional): The snapshotId of the model or model interface. Defaults to None.
        model_sid (str, optional): The SID of the model or model interface. Defaults to None.
        model_revision (int, optional): The revision of the model or model interface. Defaults to None.
        file_path_for_saving (str, optional): The path where the model should be saved. Defaults to None.

    Returns:
        dict: The model or model interface data.
    """

    model_project_item = jinko.get_project_item(
        model_core_item_id, model_snapshot_id, model_sid, revision=model_revision
    )
    if model_project_item is None:
        raise Exception("Model not found")
    if model_project_item["coreId"] is None:
        raise Exception("Model coreId not found")
    model_core_item_id = model_project_item["coreId"]["id"]
    model_snapshot_id = model_project_item["coreId"]["snapshotId"]
    model_name = model_project_item["name"]

    if item_type == "ComputationalModel":
        model = jinko.make_request(
            f"/core/v2/model_manager/jinko_model/{model_core_item_id}/snapshots/{model_snapshot_id}"
        ).json()
    else:
        model = jinko.make_request(
            f"/core/v2/model_editor/jinko_model/{model_core_item_id}/snapshots/{model_snapshot_id}"
        ).json()

    if file_path_for_saving:
        version = model_project_item.get(
            "version", {}
        )  # Ensures version is at least an empty dictionary
        if version:
            revision = version.get("revision")
            label = version.get("label")

        model_file_name = (
            item_type
            + "_"
            + model_name.replace(" ", "_")
            + "_revision_"
            + (str(revision) if revision else "")
            + ("_label_" + str(label) if label else "")
            + ".json"
        )
        local_model_file = os.path.join(file_path_for_saving, model_file_name)
        with open(local_model_file, "w") as f:
            json.dump(model, f, indent=4)
        print(f"{item_type} file successfully saved at: {local_model_file}")

    return model


def get_models_in_folder(folder_id: str):
    """
    Retrieves a dictionary of computational models from a specified folder.

    Args:
        folder_id (str): The ID of the folder containing the computational models.

    Returns:
        Dict[str, Dict[str, str]]: A dictionary where each key is a model name
        and the value is another dictionary containing 'coreItemId' and 'sid'.
    """
    models: List[Any] = jinko.make_request(
        f"/app/v1/project-item",
        params={"type": "ComputationalModel", "folderId": folder_id},
    ).json()
    # Create a dictionary mapping model names to their core ids and short ids
    model_dict = {
        m["name"]: {"coreItemId": m["coreId"]["id"], "sid": m["sid"]} for m in models
    }
    return model_dict


def upload_model_version(
    model_sid: str,
    model_file_path: str,
    version_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Uploads a model version to Jinko model manager.

    Args:
        model_sid (str): The short ID of the model to upload.
        model_file_path (str): The path to the model file in JSON format.
        version_name (Optional[str], optional): The name of the model version.
            Defaults to None.

    Returns:
        dict[str, Any]: A dictionary containing the response data from the
        model manager.

    Raises:
        FileNotFoundError: If the model file cannot be found.
        json.JSONDecodeError: If the model file is not in valid JSON format.
    """
    model_core_item_id = jinko.getCoreItemId(model_sid)["id"]
    with open(model_file_path, "r") as f:
        model = json.load(f)

    response = jinko.make_request(
        path=f"/core/v2/model_manager/jinko_model/{model_core_item_id}",
        method="PUT",
        json={"model": model},
        options={"version_name": version_name} if version_name else {},
    )
    print(
        f"Successfully uploaded model to trial {jinko.get_project_item_url_from_response(response)}"
    )
    return response.json()


def update_model_in_trial(trial_sid: str, model_core_item_id, model_snapshot_id):
    """
    Updates a clinical trial with the latest computational model version.

    Args:
        trial_sid (str): The short ID of the trial to be updated.
        model_core_item_id (str): The core item ID of the model to update the trial with.
        model_snapshot_id (str): The snapshot ID of the model version to use in the update.

    Returns:
        dict: The response data from the trial manager after the update.

    Raises:
        Exception: If the update request fails.

    """
    trial_id = jinko.get_core_item_id(trial_sid)

    # update the trial with the specified model version
    response = jinko.make_request(
        path=f"/core/v2/trial_manager/trial/{trial_id['id']}/snapshots/{trial_id['snapshotId']}",
        method="PATCH",
        json={
            "computationalModelId": {
                "coreItemId": model_core_item_id,
                "snapshotId": model_snapshot_id,
            }
        },
    )
    print(
        f"Successfully updated CM in {jinko.get_project_item_url_from_response(response)}"
    )
    return response.json()


def find_id_by_immutable_id(dicts: List[dict], target_number: int) -> Optional[str]:
    """
    Find the first dictionary in dicts where 'immutableId' equals target_number and return its 'id'.

    Args:
        dicts: List of dictionaries with 'immutableId' and 'id' keys
        target_number: The immutableId to search for

    Returns:
        The 'id' of the first matching dictionary, or None if not found
    """
    return next((d["id"] for d in dicts if d["immutableId"] == target_number), None)
