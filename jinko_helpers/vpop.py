import jinko_helpers as jinko
from jinko_helpers.types import asDict as jinko_types
import requests


def get_vpop_content(vpop_sid: str) -> jinko_types.Vpop | None:
    """
    Retrieves the JSON data of a VPOP given its SID.

    Args:
        vpop_sid (str): The SID of the Vpop.

    Returns:
        Vpop: The VPOP data containing coreVersion, metadata and patients
        None: If an HTTP error occurs during the request.
    """
    try:
        vpop_id = jinko.getProjectItem(vpop_sid)["coreId"]["id"]
        response = jinko.makeRequest(
            path=f"/core/v2/vpop_manager/vpop/{vpop_id}",
            method="GET",
        )
        return response.json()
    except requests.exceptions.HTTPError:
        return None


def get_vpop_design_content(
    vpop_design_sid: str,
) -> jinko_types.VpopDesignWithModel | None:
    """
    Retrieves the JSON data of a VpopDesign given its SID.

    Args:
        vpop_design_sid (str): The SID of the VpopDesign.

    Returns:
        VpopDesignWithModel: The VpopGVpopDesignWithModelenerator data
        None: If an HTTP error occurs during the request.
    """
    try:
        vpop_design_id = jinko.getProjectItem(vpop_design_sid)["coreId"]
        response = jinko.makeRequest(
            path=f"/core/v2/vpop_manager/vpop_generator/{vpop_design_id['id']}/snapshots/{vpop_design_id['snapshotId']}",
            method="GET",
        )
        return response.json()["contents"]
    except requests.exceptions.HTTPError:
        return None
