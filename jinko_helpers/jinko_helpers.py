"""This modules provides a set of helper functions for Jinko API

- configure authentication (jinko.initialize)
- check authentication (jinko.checkAuthentication)
- retrieve a ProjectItem (jinko.getProjectItem)
- retrieve the CoreItemId of a ProjectItem (jinko.getCoreItemId)
- make HTTP requests (jinko.makeRequest)
"""

from .__version__ import __version__
import base64 as _base64
import requests as _requests
import getpass as _getpass
import json as _json
import os as _os
import pandas as _pandas
import sqlite3 as _sqlite3
from typing import TypedDict as _TypedDict
from urllib.parse import urlparse
import warnings
import tempfile

USER_AGENT = "jinko-api-helpers-python/%s" % __version__
AUTHORIZATION_PREFIX = "Bearer"

_projectId: str | None = None
_apiKey: str | None = None
_baseUrl: str = "https://api.jinko.ai"


class CoreItemId(_TypedDict):
    """Represents the CoreItem identifier.

    Attributes:
        id (str): The unique identifier of the CoreItem.
        snapshotId (str): Identifies a specific version of the CoreItem.
    """

    id: str
    snapshotId: str


class MakeRequestOptions(_TypedDict):
    """Additional options to use when making a request to the Jinko API.

    Attributes:
        name (str): Name to use when creating/updating a ProjectItem (Modeling & Simulation).
        description (str): Description to use when creating/updating a ProjectItem (Modeling & Simulation).
        folder (str): Id of the destination folder to use when creating/updating a ProjectItem (Modeling & Simulation).
        version_name (str): Name of the new version when creating/updating a ProjectItem (Modeling & Simulation).
        input_format (str): Content type of the input payload.
        output_format (str): Expected content type of the response payload (may be ignored by server if not supported).
    """

    name: str
    description: str
    folder_id: str
    version_name: str
    input_format: str = "application/json"
    output_format: str


class ProjectItemInfoFromResponse(_TypedDict):
    """Informations contained in the "X-jinko-project-item" header returned
    by the Jinko API when creating/updating a ProjectItem (Modeling & Simulation).

    Attributes:
        sid (str): Short Id of the ProjectItem.
        description (str): Type of the ProjectItem.
        coreItemId (CoreItemId): CoreItemId of the ProjectItem.
        revision (int): Revision number of the ProjectItem.
    """

    sid: str
    kind: str
    coreItemId: CoreItemId
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
        "X-jinko-project-id": _projectId,
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
    json=None,
    csv_data=None,
    options: MakeRequestOptions = None,
    data=None,
):
    """Makes an HTTP request to the Jinko API.

    Args:
        path (str): HTTP path
        method (str, optional): HTTP method. Defaults to 'GET'
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

    headers["Content-Type"] = input_mime_type
    if output_mime_type is not None:
        headers["Accept"] = output_mime_type

    # Make the request
    response = _requests.request(
        method,
        _baseUrl + path,
        headers=headers,
        **({data_param: data} if data_param else {}),
    )
    if response.status_code not in [200, 204]:
        if (
            "content-type" in response.headers
            and response.headers["content-type"] == "application/json"
        ):
            print(response.json())
        else:
            print("%s: %s" % (response.status_code, response.text))
        response.raise_for_status()
    if response.status_code == 204:
        return "Query successfully done, got a 204 response"
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
) -> list[any]:
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
        print(response.json())
        response.raise_for_status()
    return True


def initialize(
    projectId: str | None = None, apiKey: str | None = None, baseUrl: str | None = None
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
            baseUrl='http://localhost:8000'
        )
    """
    global _projectId, _apiKey, _baseUrl
    if baseUrl is not None:
        _baseUrl = baseUrl
    else:
        baseUrlFromEnv = _os.environ.get("JINKO_BASE_URL")
        if baseUrlFromEnv is not None and baseUrlFromEnv.strip() != "":
            _baseUrl = baseUrlFromEnv.strip()
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
        print(message)
        raise Exception(message)

    # Ask user for API key/projectId and check authentication
    if _projectId is None or _projectId.strip() == "":
        _projectId = _getpass.getpass("Please enter your Project Id")
    if _projectId.strip() == "":
        message = "Project Id cannot be empty"
        print(message)
        raise Exception(message)

    if not checkAuthentication():
        message = 'Authentication failed for Project "%s"' % (_projectId)
        print(message)
        raise Exception(message)
    print("Authentication successful")


def getProjectItem(shortId: str, revision: int | None = None) -> dict:
    """Retrieves a single ProjectItem from its short Id
    and optionally its revision number

    Args:
        shortId (str): short Id of the ProjectItem
        revision (int | None, optional): revision number. Defaults to None

    Returns:
        dict: ProjectItem

    Raises:
        Exception: if HTTP status code is not 200

    Examples:
        projectItem = jinko.getProjectItem('tr-EUsp-WjjI')

        projectItem = jinko.getProjectItem('tr-EUsp-WjjI', 1)
    """
    if revision is None:
        return makeRequest("/app/v1/project-item/%s" % (shortId)).json()
    else:
        return makeRequest(
            "/app/v1/project-item/%s?revision=%s" % (shortId, revision)
        ).json()


def getCoreItemId(shortId: str, revision: int | None = None) -> CoreItemId:
    """Retrieves the CoreItemId corresponding to a ProjectItem

    Args:
        shortId (str): short Id of the ProjectItem
        revision (int | None, optional): revision number. Defaults to None

    Returns:
        CoreItemId: corresponding CoreItemId

    Raises:
        Exception: if HTTP status code is not 200
        Exception: if this type of ProjectItem has no CoreItemId

    Examples:
        id = jinko.getCoreItemId('tr-EUsp-WjjI')

        id = jinko.getCoreItemId('tr-EUsp-WjjI', 1)
    """
    item = getProjectItem(shortId, revision)
    if "coreId" not in item or item["coreId"] is None:
        message = 'ProjectItem "%s" has no CoreItemId' % (shortId)
        print(message)
        raise Exception(message)
    return item["coreId"]


def dataTableToSQLite(
    data_table_file_path: str,
):
    """
    Converts a CSV file to an SQLite database and encodes it in base64.

    Args:
        data_table_file_path (str): The path to the CSV file.

    Returns:
        str: The encoded SQLite database.

    Raises:
        FileNotFoundError: If the CSV file does not exist.

    Examples:
        >>> datTableToSQLite('path/to/data.csv')
        'encoded_data_table'
    """
    # Step 1: Convert CSV to SQLite

    # Read the CSV file
    df = _pandas.read_csv(data_table_file_path)
    column_names = df.columns.tolist()

    # Connect to SQLite database (or create it)
    data_table_sqlite_file_path = _os.path.splitext(data_table_file_path)[0] + ".sqlite"
    conn = _sqlite3.connect(data_table_sqlite_file_path)
    cursor = conn.cursor()

    # Write the DataFrame to the SQLite database
    df.to_sql(
        "data",
        conn,
        if_exists="replace",
        index=False,
        dtype={col: "TEXT" for col in df.columns},
    )

    # Create the 'data_columns' table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS data_columns (
        name TEXT UNIQUE,
        realname TEXT UNIQUE
    )
    """
    )

    # Insert column data into 'data_columns' table
    for name in column_names:
        cursor.execute(
            "INSERT OR IGNORE INTO data_columns (name, realname) VALUES (?, ?)",
            (name, name),
        )

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    # Step 2: Encode SQLite database in base64
    with open(data_table_sqlite_file_path, "rb") as f:
        encoded_data_table = _base64.b64encode(f.read()).decode("utf-8")

    return encoded_data_table


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
    url = f"https://jinko.ai/{sid}"
    return url


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
    url = f"https://jinko.ai/{sid}"
    return f"Resource link: {url}"

def is_interactive():
    """Check if the environment supports interactive plot display (like Jupyter or IPython)."""
    try:
        # Check if in an IPython environment
        __IPYTHON__
        return True
    except NameError:
        return False

def show_plot_conditionally(fig, file_name = None):
    """Show the plot if in an interactive environment, otherwise save it."""
    if is_interactive():
        # If in a supported interactive environment, show the plot
        fig.show()
    else:
        # Fallback: Save the plot to a file if show() is not supported
        tmp_fd = None
        if file_name is None:
            (tmp_fd, file_name) = tempfile.mkstemp('.html')
        try:
          fig.write_html(file_name)
        except Exception as e:            
          if tmp_fd is not None:
            _os.unlink(file_name)
          raise
        print(f"Plot saved to {file_name} . Please open it in a web browser.")