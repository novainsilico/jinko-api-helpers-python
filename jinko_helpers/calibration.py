import jinko_helpers as jinko
from jinko_helpers.types import asDict as jinko_types
import requests


def get_calib_status(calib_core_id: jinko.CoreItemId) -> jinko_types.JobStatus | None:
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
