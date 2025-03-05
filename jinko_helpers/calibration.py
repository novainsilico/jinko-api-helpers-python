import jinko_helpers as jinko
import requests
from typing import List, Optional


def get_calib_status(calib_core_id):
    """
    Retrieves the calibration status for a given calibration core ID.

    Args:
        calib_core_id (CoreItemId): The CoreItemId of the calibration.

    Returns:
        JobStatus: A string in ['completed', 'running', 'not_launched', 'stopped', 'error']
        None: If an HTTP error occurs during the request.
    """
    try:
        response = jinko.makeRequest(
            path=f"/core/v2/calibration_manager/calibration/{calib_core_id['id']}/snapshots/{calib_core_id['snapshotId']}/status",
            method="GET",
        )
        return response.json()
    except requests.exceptions.HTTPError:
        return None


def get_latest_calib_with_status(
    shortId: str,
    statuses: List,
) -> dict:
    """
    Retrieve the latest calibration whose status is a member of the prescribed list of statuses

    Args:
        core_item_id (str): The CoreItemId of the Calibration
        statuses (list of str): The snapshotId of the ProjectItem.
    Returns:
        core ID dictionary
        Dictionary Attributes:
            coreItemId (str): The unique identifier of the CoreItem.
            snapshotId (str): Identifies a specific version of the CoreItem.

    Raises:
        ValueError: If no calibration having the prescribed status is found
    """

    core_item_id = jinko.getCoreItemId(shortId=shortId)["id"]
    versions = jinko.make_request(
        f"/core/v2/calibration_manager/calibration/{core_item_id}/status"
    ).json()
    try:
        latest_version = next(item for item in versions if item["status"] in statuses)
        return latest_version["simulationId"]
    except StopIteration:
        raise ValueError(f"Found no calibration with status among {statuses}")
