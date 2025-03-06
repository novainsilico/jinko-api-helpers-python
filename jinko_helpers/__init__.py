"""
jinko_helpers package initialization.

This package provides helper functions for interacting with the Jinko API.
"""

import warnings


def deprecate_alias(old_name, new_name, new_func):
    """A decorator to create deprecated aliases for functions."""

    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{old_name} is deprecated and will be removed in a future version. "
            f"Please use {new_name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return new_func(*args, **kwargs)

    return wrapper


from .jinko_helpers import (
    initialize,
    checkAuthentication as _check_authentication,
    getCoreItemId as _get_core_item_id,
    makeRequest as _make_request,
    getProjectItemInfoFromResponse as _get_project_item_info_from_response,
    getProjectItemUrlFromSid as _get_project_item_url_from_sid,
    getProjectItemUrlFromResponse as _get_project_item_url_from_response,
    nextPage as _next_page,
    fetchAllJson as _fetch_all_json,
    getProjectItemUrlByCoreItemId as _get_project_item_url_by_core_item_id,
    show_plot_conditionally,
    list_project_item_versions,
    get_project_item,
    get_sid_revision_from_url,
    MakeRequestOptions,
    ProjectItemInfoFromResponse,
)

from .calibration import get_calib_status, get_latest_calib_with_status

from .model import (
    get_models_in_folder,
    download_model,
    download_model_interface,
    upload_model_version,
    update_model_in_trial,
    find_id_by_immutable_id,
)

from .data_table import data_table_to_sqlite, df_to_sqlite, csv_to_df

# Apply deprecations with the proper decorator
checkAuthentication = deprecate_alias(
    "checkAuthentication", "check_authentication", _check_authentication
)
getCoreItemId = deprecate_alias("getCoreItemId", "get_core_item_id", _get_core_item_id)
makeRequest = deprecate_alias("makeRequest", "make_request", _make_request)
dataTableToSQLite = deprecate_alias(
    "dataTableToSQLite", "data_table_to_sqlite", data_table_to_sqlite
)
getProjectItemInfoFromResponse = deprecate_alias(
    "getProjectItemInfoFromResponse",
    "get_project_item_info_from_response",
    _get_project_item_info_from_response,
)
getProjectItemUrlFromSid = deprecate_alias(
    "getProjectItemUrlFromSid",
    "get_project_item_url_from_sid",
    _get_project_item_url_from_sid,
)
getProjectItemUrlFromResponse = deprecate_alias(
    "getProjectItemUrlFromResponse",
    "get_project_item_url_from_response",
    _get_project_item_url_from_response,
)
nextPage = deprecate_alias("nextPage", "next_page", _next_page)
fetchAllJson = deprecate_alias("fetchAllJson", "fetch_all_json", _fetch_all_json)
getProjectItemUrlByCoreItemId = deprecate_alias(
    "getProjectItemUrlByCoreItemId",
    "get_project_item_url_by_core_item_id",
    _get_project_item_url_by_core_item_id,
)

# Assign snake_case versions directly
check_authentication = _check_authentication
get_core_item_id = _get_core_item_id
make_request = _make_request
get_project_item_info_from_response = _get_project_item_info_from_response
get_project_item_url_from_sid = _get_project_item_url_from_sid
get_project_item_url_from_response = _get_project_item_url_from_response
next_page = _next_page
fetch_all_json = _fetch_all_json
get_project_item_url_by_core_item_id = _get_project_item_url_by_core_item_id

from .trial import (
    is_trial_completed,
    monitor_trial_until_completion,
    is_trial_running,
)

from .vpop import (
    get_vpop_content,
    get_vpop_design_content,
)

# Import version from version.py
from .__version__ import __version__

__all__ = [
    "__version__",
    "initialize",
    "checkAuthentication",
    "check_authentication",
    "get_project_item",
    "getCoreItemId",
    "get_core_item_id",
    "makeRequest",
    "make_request",
    "dataTableToSQLite",
    "data_table_to_sqlite",
    "getProjectItemInfoFromResponse",
    "get_project_item_info_from_response",
    "getProjectItemUrlFromSid",
    "get_project_item_url_from_sid",
    "getProjectItemUrlFromResponse",
    "get_project_item_url_from_response",
    "nextPage",
    "next_page",
    "fetchAllJson",
    "fetch_all_json",
    "getProjectItemUrlByCoreItemId",
    "get_project_item_url_by_core_item_id",
    "monitor_trial_until_completion",
    "is_trial_completed",
    "is_trial_running",
    "show_plot_conditionally",
    "get_vpop_content",
    "get_vpop_design_content",
    "list_project_item_versions",
    "get_project_item",
    "get_sid_revision_from_url",
    "MakeRequestOptions",
    "ProjectItemInfoFromResponse",
    "get_calib_status",
    "get_latest_calib_with_status",
    "get_models_in_folder",
    "download_model",
    "download_model_interface",
    "upload_model_version",
    "update_model_in_trial",
    "find_id_by_immutable_id",
    "df_to_sqlite",
    "data_table_to_sqlite",
    "csv_to_df",
]
