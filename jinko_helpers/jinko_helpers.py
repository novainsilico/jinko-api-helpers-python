"""This modules provides a set of helper functions for Jinko API

- configure authentication (jinko.initialize)
- check authentication (jinko.checkAuthentication)
- retrieve a ProjectItem (jinko.get_project_item)
- retrieve the CoreItemId of a ProjectItem (jinko.getCoreItemId)
- make HTTP requests (jinko.makeRequest)
"""

import sys

from .__version__ import __version__
import base64 as _base64
import requests as _requests
import getpass as _getpass
import json as _json
import os as _os
from typing import List, Any, Optional, TypedDict
from urllib.parse import urlparse
import warnings
import tempfile
import re

USER_AGENT = "jinko-api-helpers-python/%s" % __version__
AUTHORIZATION_PREFIX = "Bearer"

_projectId: str | None = None
_apiKey: str | None = None
_baseUrl: str = "https://api.jinko.ai"
_jinkoUrl: str = "https://jinko.ai"


class CoreItemIdDict(TypedDict):
    """Represents the CoreItem identifier.

    Attributes:
        id (str): The unique identifier of the CoreItem.
        snapshotId (str): Identifies a specific version of the CoreItem.
    """

    id: str
    snapshotId: str


class MakeRequestOptions(TypedDict, total=False):
    """Additional options to use when making a request to the Jinko API.

    Attributes:
        name (str): Name to use when creating/updating a ProjectItem (Modeling & Simulation).
        description (str): Description to use when creating/updating a ProjectItem (Modeling & Simulation).
        folder (str): Id of the destination folder to use when creating/updating a ProjectItem (Modeling & Simulation).
        version_name (str): Name of the new version when creating/updating a ProjectItem (Modeling & Simulation).
        input_format (str): Content type of the input payload.
        output_format (str): Expected content type of the response payload (may be ignored by server if not supported).
    """

    name: Optional[str]
    description: Optional[str]
    folder_id: Optional[str]
    version_name: Optional[str]
    input_format: Optional[str]
    output_format: Optional[str]


class ProjectItemInfoFromResponse(TypedDict):
    """Informations contained in the "X-jinko-project-item" header returned
    by the Jinko API when creating/updating a ProjectItem (Modeling & Simulation).

    Attributes:
        sid (str): Short Id of the ProjectItem.
        description (str): Type of the ProjectItem.
        coreItemId (CoreItemIdDict): CoreItemI dictionnary of the ProjectItem.
        revision (int): Revision number of the ProjectItem.
    """

    sid: str
    kind: str
    coreItemId: CoreItemIdDict
    revision: int


_headers_map = {
    "name": "X-jinko-project-item-name",
    "description": "X-jinko-project-item-description",
    "folder_id": "X-jinko-project-item-folder-ids",
    "version_name": "X-jinko-project-item-version-name",
}


def _getHeaders() -> dict[str, str]:
    apiKey = _apiKey
    if apiKey is None:
        apiKey = ""
    return {
        "X-jinko-project-id": _projectId,  # type: ignore
        "Authorization": "%s %s" % (AUTHORIZATION_PREFIX, apiKey),
        "User-Agent": USER_AGENT,
    }


def encodeCustomHeaders(options: MakeRequestOptions) -> dict:
    """Encodes and prepares custom headers for the Jinko API.

    Args:
        custom_data (dict): Dictionary containing 'description', 'folder_id', 'name', 'version_name', 'output_format', 'input_format'

    Returns:
        dict: Dictionary containing encoded and formatted headers.
    """
    headers = {}
    for key, header_name in _headers_map.items():
        if key in options:
            value = options[key]
            if key == "folder_id":
                value = _json.dumps([{"id": value, "action": "add"}])
            headers[header_name] = _base64.b64encode(value.encode("utf-8")).decode(
                "utf-8"
            )
    return headers


def makeUrl(path: str):
    return _baseUrl + path


def makeRequest(
    path: str,
    method: str = "GET",
    params=None,
    json=None,
    csv_data=None,
    options: MakeRequestOptions | None = None,
    data=None,
) -> _requests.Response:
    """Makes an HTTP request to the Jinko API.

    Args:
        path (str): HTTP path
        method (str, optional): HTTP method. Defaults to 'GET'
        params (Dict, optional): Dictionary, list of tuples or bytes to send in the query string. Defaults to None
        json (Any, optional): input payload as JSON. Defaults to None
        csv_data (str, optional): input payload as a CSV formatted string. Defaults to None
        options (MakeRequestOptions, optional): additional options. Defaults to None
        data: (Any, optional): raw input payload. Defaults to None
    Returns:
        Response: HTTP response object

    Raises:
        requests.exceptions.HTTPError: if HTTP status code is not 200

    Examples:
        response = makeRequest('/app/v1/auth/check')

        projectItem = makeRequest(
            '/app/v1/project-item/tr-EUsp-WjjI',
            method='GET',
        ).json()

        # pass query parameters
        projectItem = makeRequest(
            '/app/v1/project-item',
            params={
              "name": "Example",
              "type": ["ComputationalModel", "Trial"],
            },
            method='GET',
        ).json()

        # receive data in CSV format
        response = makeRequest('/core/v2/vpop_manager/vpop/9c9c0bc5-f447-4745-b5eb-41b18e5eb900',
            options={
                'output_format': 'text/csv'
            }
        )

        # send data in CSV format
        response = makeRequest('/core/v2/vpop_manager/vpop', method='POST',
            data="....",
            options={
                'input_format': 'text/csv'
            }
        )
    """
    # Get the default headers from _getHeaders()
    headers = _getHeaders()

    input_mime_type = "application/json"
    output_mime_type = None

    # Encode custom headers as base64 and update the default headers
    if options:
        if "input_format" in options:
            input_mime_type = options["input_format"]
        if "output_format" in options:
            output_mime_type = options["output_format"]
        encoded_custom_headers = encodeCustomHeaders(options)
        headers.update(encoded_custom_headers)

    # Use the appropriate data parameter based on whether json or csv_data is provided
    if json is not None:
        data = json
        data_param = "json"
        input_mime_type = "application/json"
    elif csv_data is not None:
        data = csv_data
        input_mime_type = "text/csv"
        data_param = "data"
    elif data is not None:
        data_param = "data"
    else:
        data_param = None

    if input_mime_type:
        headers["Content-Type"] = input_mime_type
    if output_mime_type is not None:
        headers["Accept"] = output_mime_type

    # Make the request
    response = _requests.request(
        method,
        _baseUrl + path,
        headers=headers,
        params=params,
        **({data_param: data} if data_param else {}),  # type: ignore
    )
    if response.status_code not in [200, 204]:
        if (
            "content-type" in response.headers
            and response.headers["content-type"] == "application/json"
        ):
            sys.stderr.write(response.json() + "\n")
        else:
            sys.stderr.write("%s: %s\n" % (response.status_code, response.text))
        response.raise_for_status()
    if response.status_code == 204:
        sys.stderr.write("Query successfully done, got a 204 response\n")
    return response


def nextPage(lastResponse: _requests.Response) -> _requests.Response | None:
    """Retrieves the next page of a response

    Args:
        lastResponse (Response): HTTP response object to retrieve next page for

    Returns:
        Response|None: HTTP response object for next page or None if there is no next page

    Raises:
        Exception: if HTTP status code is not 200

    Examples:
        response = makeRequest('/app/v1/project-item')
        response = nextPage(response)
    """
    link = lastResponse.links.get("next")
    if link is None:
        return None

    url = urlparse(link["url"])
    return makeRequest(
        path="%s?%s" % (url.path, url.query),
        method="GET",
    )


def fetchAllJson(
    path: str,
) -> list[Any]:
    """Makes a GET HTTP request and retrieve all pages of a paginated response as json

    Args:
        path (str): HTTP path

    Returns:
        Response: HTTP response object

    Raises:
        Exception: if HTTP status code is not 200

    Examples:
        trials = fetchAllJson('/app/v1/project-item/?type=Trial')
    """
    list = []
    response = makeRequest(path)
    while True:
        list.extend(response.json())
        response = nextPage(response)
        if response is None:
            break
    return list


def checkAuthentication() -> bool:
    """Checks authentication

    Returns:
        bool: whether or not authentication was successful

    Raises:
        Exception: if HTTP status code is not one of [200, 401]

    Examples:
        if not jinko.checkAuthentication():
            print('Authentication failed')
    """
    response = _requests.get(makeUrl("/app/v1/auth/check"), headers=_getHeaders())
    if response.status_code == 401:
        return False
    if response.status_code != 200:
        sys.stderr.write(response.json() + "\n")
        response.raise_for_status()
    return True


def initialize(
    projectId: str | None = None,
    apiKey: str | None = None,
    baseUrl: str | None = None,
    jinkoUrl: str | None = None,
):
    """Configures the connection to Jinko API and checks authentication

    Args:
        projectId (str | None, optional): project Id. Defaults to None
            If None, fallbacks to JINKO_PROJECT_ID environment variable
            If environment variable is not set, you will be asked for it interactively
        apiKey (str | None, optional): API key value. Defaults to None
            If None, fallbacks to JINKO_API_KEY environment variable
            If environment variable is not set, you will be asked for it interactively
        baseUrl (str | None, optional): root url to reach Jinko API. Defaults to None
            If None, fallbacks to JINKO_BASE_URL environment variable
            If environment variable is not set, fallbacks to 'https://api.jinko.ai'
        jinkoUrl (str | None, optional): root url to reach Jinko front-end. Defaults to None
            If None, fallbacks to JINKO_URL environment variable
            If environment variable is not set, fallbacks to 'https://jinko.ai'

    Raises:
        Exception: if API key is empty
        Exception: if Project Id is empty
        Exception: if authentication is invalid

    Examples:
        jinko.initialize()

        jinko.initialize(
            '016140de-1753-4133-8cbf-e67d9a399ec1',
            apiKey='50b5085e-3675-40c9-b65b-2aa8d0af101c'
        )

        jinko.initialize(
            baseUrl='http://localhost:8000',
            jinkoUrl='http://localhost:3000'
        )
    """
    global _projectId, _apiKey, _baseUrl, _jinkoUrl
    if baseUrl is not None:
        _baseUrl = baseUrl
    else:
        baseUrlFromEnv = _os.environ.get("JINKO_BASE_URL")
        if baseUrlFromEnv is not None and baseUrlFromEnv.strip() != "":
            _baseUrl = baseUrlFromEnv.strip()

    if jinkoUrl is not None:
        _jinkoUrl = jinkoUrl
    else:
        jinkoUrlFromEnv = _os.environ.get("JINKO_URL")
        if jinkoUrlFromEnv is not None and jinkoUrlFromEnv.strip() != "":
            _jinkoUrl = jinkoUrlFromEnv.strip()

    if apiKey is not None:
        _apiKey = apiKey
    else:
        _apiKey = _os.environ.get("JINKO_API_KEY")
    if projectId is not None:
        _projectId = projectId
    else:
        _projectId = _os.environ.get("JINKO_PROJECT_ID")

    if _apiKey is None or _apiKey.strip() == "":
        _apiKey = _getpass.getpass("Please enter your API key")
    if _apiKey.strip() == "":
        message = "API key cannot be empty"
        sys.stderr.write(message + "\n")
        raise Exception(message)

    # Ask user for API key/projectId and check authentication
    if _projectId is None or _projectId.strip() == "":
        _projectId = _getpass.getpass("Please enter your Project Id")
    if _projectId.strip() == "":
        message = "Project Id cannot be empty"
        sys.stderr.write(message + "\n")
        raise Exception(message)

    if not checkAuthentication():
        message = 'Authentication failed for Project "%s"' % (_projectId)
        sys.stderr.write(message + "\n")
        raise Exception(message)
    sys.stderr.write("Authentication successful\n")


def getCoreItemId(shortId: str, revision: int | None = None) -> CoreItemIdDict:
    """Retrieves the CoreItemId dictionnary corresponding to a ProjectItem

    Args:
        shortId (str): short Id of the ProjectItem
        revision (int | None, optional): revision number. Defaults to None

    Returns:
        CoreItemIdDict: corresponding CoreItemId dictionnary

    Raises:
        Exception: if HTTP status code is not 200
        Exception: if this type of ProjectItem has no CoreItemId

    Examples:
        id = jinko.getCoreItemId('tr-EUsp-WjjI')

        id = jinko.getCoreItemId('tr-EUsp-WjjI', 1)
    """
    item = get_project_item(sid=shortId, revision=revision)
    if "coreId" not in item or item["coreId"] is None:
        message = 'ProjectItem "%s" has no CoreItemId' % (shortId)
        sys.stderr.write(message + "\n")
        raise Exception(message)
    return item["coreId"]


def getProjectItemInfoFromResponse(
    response: _requests.Response,
) -> ProjectItemInfoFromResponse | None:
    """Retrieves the information contains in the "X-jinko-project-item"
    header of the response

    Args:
        response (Response): HTTP response object

    Returns:
        ProjectItemInfoFromResponse | None: ProjectItem informations or None if header does not exist

    Raises:
        Exception: if HTTP status code is not 200

    Examples:
      >>> response = jinko.makeRequest(
      ...     path="/core/v2/model_manager/jinko_model",
      ...     method="POST",
      ...     json={"model": model, "solvingOptions": solving_options},
      ... )
      >>> jinko.getProjectItemInfoFromResponse(response)
      {"sid": "cm-pKGA-7r3O", "kind": "ComputationalModel", "coreItemId": {"id": "be812bcc-978e-4fe1-b8af-8fb521888718", "snapshotId": "ce2b76f6-07dd-47c6-9700-c70ce44f0507"}, "revision": 5}
    """
    base64Content = response.headers.get("x-jinko-project-item")
    if base64Content is None:
        return None
    jsonContent = _base64.b64decode(base64Content)
    return _json.loads(jsonContent)


def getProjectItemUrlFromSid(sid: str):
    """
    Retrieves the URL of a ProjectItem based on its SID.

    Args:
        sid (str): The SID of the ProjectItem.

    Returns:
        str: The URL of the ProjectItem.
    """
    url = f"{_jinkoUrl}/{sid}"
    return url


def get_sid_revision_from_url(url: str) -> tuple[str | None, int | None]:
    """
    Return the sid and revision number from a jinko URL.

    Args:
        url (str): The URL of a Jinko ProjectItem.

    Returns:
        tuple[str | None, int | None]: The sid and revision number of the ProjectItem, or None if the URL does not match the expected pattern.

    Examples:
        >>> jinko.get_sid_revision_from_url("https://jinko.ai/ca-foo-bar")
        ("ca-foo-bar", None)
        >>> jinko.get_sid_revision_from_url("https://jinko.ai/ca-foo-bar?revision=42")
        ("ca-foo-bar", 42)
    """
    # start with a generic URL match
    pattern = (
        r"^"
        r"((?P<schema>.+?)://)?"
        r"(?P<host>.*?)"
        r"(:(?P<port>\d+?))?"
        r"(/(?P<path>.*?))?"
        r"(?P<query>[?].*?)?"
        r"$"
    )
    regex = re.compile(pattern)
    match = regex.match(url)
    if match is None:
        return None, None
    # sid should directly follow the base URL
    path = match.groupdict()["path"]
    if not path or "/" in path:
        return None, None
    sid = path
    # revision number should be an integer
    query = match.groupdict()["query"]
    try:
        revision = int(query.split("revision=")[1]) if query is not None else None
    except ValueError:
        revision = None
    return sid, revision


def getProjectItemUrlFromResponse(response: _requests.Response):
    """
    Retrieves the URL of a ProjectItem from an HTTP response object.

    Args:
        response (Response): HTTP response object.

    Returns:
        str: The URL of the ProjectItem.

    Raises:
        Exception: if the "X-jinko-project-item" header is not present in the response.
    """
    project_item_info = getProjectItemInfoFromResponse(response)
    if project_item_info is None:
        raise Exception(
            "The 'X-jinko-project-item' header is not present in the response."
        )
    sid = project_item_info["sid"]
    url = getProjectItemUrlFromSid(sid)
    return url


def getProjectItemUrlByCoreItemId(coreItemId: str):
    """
    Retrieves the URL of a ProjectItem based on its CoreItemId.
    Args:
        coreItemId (str): The CoreItemId of the ProjectItem.
    Returns:
        str: The URL of the ProjectItem.
    Raises:
        requests.exceptions.RequestException: If there is an error making the request.
    Examples:
        >>> getProjectItemUrlByCoreItemId("123456789")
        'https://jinko.ai/foo'
    """
    warnings.warn(
        "getProjectItemUrlByCoreItemId is deprecated and will be removed in a future version,"
        + "use getProjectItemUrlFromResponse instead",
        category=DeprecationWarning,
    )
    response = makeRequest("/app/v1/core-item/%s" % (coreItemId)).json()
    sid = response.get("sid")
    url = f"{_jinkoUrl}/{sid}"
    return f"Resource link: {url}"


def is_interactive():
    """Check if the environment supports interactive plot display (like Jupyter or IPython)."""
    try:
        # Check if in an IPython environment
        __IPYTHON__  # type: ignore
        return True
    except NameError:
        return False


def show_plot_conditionally(fig, file_name=None):
    """Show the plot if in an interactive environment, otherwise save it."""
    if is_interactive():
        # If in a supported interactive environment, show the plot
        fig.show()
    else:
        # Fallback: Save the plot to a file if show() is not supported
        tmp_fd = None
        if file_name is None:
            (tmp_fd, file_name) = tempfile.mkstemp(".html")
        try:
            fig.write_html(file_name)
        except Exception as e:
            if tmp_fd is not None:
                _os.unlink(file_name)
            raise
        print(f"Plot saved to {file_name} . Please open it in a web browser.")


def list_project_item_versions(sid: str, only_labeled: bool = False):
    """
    Retrieve the list of versions of a given ProjectItem.

    Args:
        sid (str): The short ID of the ProjectItem.
        only_labeled (bool, optional): If True, only return labeled versions. Defaults to False.

    Returns:
        List[ProjectItemVersion]: The list of versions of the ProjectItem.
    """
    only_labeled_str = "true" if only_labeled else "false"
    response = makeRequest(
        f"/app/v1/project-item/{sid}/versions",
        params={"onlyLabeled": only_labeled_str},
    )
    return response.json()


def get_project_item(
    core_item_id=None,
    snapshot_id=None,
    sid: Optional[str] = None,
    url: Optional[str] = None,
    revision: Optional[float] = None,
    label: Optional[str] = None,
):
    """
    Retrieve a ProjectItem from its CoreItemId, snapshotId, or its SID and revision.

    Args:
        core_item_id (str, optional): The CoreItemId of the ProjectItem.
        snapshot_id (str, optional): The snapshotId of the ProjectItem.
        sid (str, optional): The SID of the ProjectItem.
        url (str, optional): The URL of the ProjectItem.
        revision (int, optional): The revision of the ProjectItem.
        label (str, optional): The label of the ProjectItem.

    Returns:
        ProjectItem, optional: The retrieved ProjectItem, or None if not found.

    Raises:
        ValueError: If neither 'sid' nor 'core_item_id' is provided.
        Exception: If the parameters are ambiguous, i.e. they do not point to the same project item.
    """
    if url and not sid:
        sid, _ = get_sid_revision_from_url(url)

    if core_item_id:
        return makeRequest(
            path=f"/app/v1/core-item/{core_item_id}", params={"snapshotId": snapshot_id}
        ).json()
    elif sid:
        if revision:
            return makeRequest(
                path=f"/app/v1/project-item/{sid}", params={"revision": revision}
            ).json()
        elif label:
            labeled_versions = makeRequest(
                path=f"/app/v1/project-item/{sid}/versions?onlyLabeled=true"
            ).json()
            try:
                return next(x for x in labeled_versions if x["label"] == label)
            except StopIteration:
                raise ValueError(f"Unknown version label {label}")
        else:
            return makeRequest(path=f"/app/v1/project-item/{sid}").json()
    else:
        raise ValueError("You must provide either 'sid' or 'core_item_id'")
