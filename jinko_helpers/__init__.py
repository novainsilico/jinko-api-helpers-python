"""
jinko_helpers package initialization.

This package provides helper functions for interacting with the Jinko API.
"""

from .jinko_helpers import (
    initialize,
    checkAuthentication,
    getProjectItem,
    getCoreItemId,
    makeRequest,
    encodeCustomHeaders,
    makeUrl,
    dataTableToSQLite,
    getProjectItemInfoFromResponse,
    getProjectItemUrlFromSid,
    getProjectItemUrlFromResponse,
    nextPage,
    fetchAllJson,
    getProjectItemUrlByCoreItemId,
    CoreItemId,
    MakeRequestOptions,
    ProjectItemInfoFromResponse,
)

from .trial import (
    monitor_trial_until_completion,
    is_trial_running,
)

# Import version from version.py
from .__version__ import __version__

__all__ = [
    "__version__",
    "initialize",
    "checkAuthentication",
    "getProjectItem",
    "getCoreItemId",
    "makeRequest",
    "encodeCustomHeaders",
    "makeUrl",
    "dataTableToSQLite",
    "getProjectItemInfoFromResponse",
    "getProjectItemUrlFromSid",
    "getProjectItemUrlFromResponse",
    "nextPage",
    "fetchAllJson",
    "getProjectItemUrlByCoreItemId",
    "CoreItemId",
    "MakeRequestOptions",
    "ProjectItemInfoFromResponse",
    "monitor_trial_until_completion",
    "is_trial_running",
]
