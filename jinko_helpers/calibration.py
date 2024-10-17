import jinko_helpers as jinko
import requests


def get_calib_status(calib_core_id):
    """
    Retrieves the calibration status for a given calibration core ID.

    Args:
        calib_core_id (dict): A dictionary containing 'id' (for the coreItemId) and 'snapshotId' keys for the calibration.

    Returns:
        dict: A JSON object representing the calibration status if the request is successful.
        str: An empty string if an HTTP error occurs during the request.
    """
    try:
        response = jinko.makeRequest(
            path=f"/core/v2/calibration_manager/calibration/{calib_core_id['id']}/snapshots/{calib_core_id['snapshotId']}/status",
            method="GET",
        )
        return response.json()
    except requests.exceptions.HTTPError:
        return ""
