import jinko_helpers as jinko
import requests
import pandas as pd


def get_vpop_content(vpop_sid: str):
    """
    Retrieves the JSON data of a VPOP given its SID.

    Args:
        vpop_sid (str): The SID of the Vpop.

    Returns:
        Vpop: The VPOP data containing coreVersion, metadata and patients
        None: If an HTTP error occurs during the request.
    """
    try:
        vpop_id = jinko.get_project_item(sid=vpop_sid)["coreId"]["id"]
        response = jinko.makeRequest(
            path=f"/core/v2/vpop_manager/vpop/{vpop_id}",
            method="GET",
        )
        return response.json()
    except requests.exceptions.HTTPError:
        return None


def get_vpop_design_content(
    vpop_design_sid: str,
):
    """
    Retrieves the JSON data of a VpopDesign given its SID.

    Args:
        vpop_design_sid (str): The SID of the VpopDesign.

    Returns:
        VpopDesignWithModel: The VpopGVpopDesignWithModelenerator data
        None: If an HTTP error occurs during the request.
    """
    try:
        vpop_design_id = jinko.get_project_item(sid=vpop_design_sid)["coreId"]
        response = jinko.makeRequest(
            path=f"/core/v2/vpop_manager/vpop_generator/{vpop_design_id['id']}/snapshots/{vpop_design_id['snapshotId']}",
            method="GET",
        )
        return response.json()["contents"]
    except requests.exceptions.HTTPError:
        return None


def subsampling_goodness_of_fit_as_dataframe(fitness: dict):
    """
    Converts the goodness of fit as returned by the "/core/v2/vpop_manager/vpop_generator/{subsampling_core_item_id}/snapshots/{subsampling_snapshot_id}/vpop"
    route to a pandas dataframe

    Args:
        fitness (dict): the goodness of fit as returned by the aforementioned route

    Returns:
        the goodness of fit in the form of a Pandas dataframe
    """
    return pd.DataFrame(
        [
            {
                "qoi": x["id"],
                "arm": x["arm"],
                "score": x["score"],
                "targetType": "marginal",
            }
            for x in fitness["marginals"]
        ]
        + [
            {
                "qoi": x["id"],
                "arm": x["arm"],
                "score": x["score"],
                "targetType": "categorical",
            }
            for x in fitness["categoricals"]
        ]
        + [
            {
                "qoi": x["id"],
                "arm": x["arm"],
                "score": x["score"],
                "targetType": "survival",
            }
            for x in fitness["survivals"]
        ]
        + [
            {
                "qoi": x["id"],
                "arm": x["arm"],
                "score": x["score"],
                "targetType": "summary statistics",
            }
            for x in fitness["summaryStatistics"]
        ]
        + [
            {
                "qoi": x["correlateX"]["id"],
                "arm": x["correlateX"].get("arm"),
                "score": x["score"],
                "targetType": "correlation",
                "qoi2": x["correlateY"]["id"],
                "arm2": x["correlateY"].get("arm"),
            }
            for x in fitness["correlations"]
        ]
    )
