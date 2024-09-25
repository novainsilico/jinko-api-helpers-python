"""Utility functions used in the crabbit package."""

__all__ = [
    "get_sid_revision_from_url",
    "to_bold",
    "clear_directory",
    "get_calib_status",
]

import shutil
import os
import re
import requests

import jinko_helpers as jinko


def get_sid_revision_from_url(url):
    """Return the sid and revision number from a jinko URL."""
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


def to_bold(text):
    """Return bold text to print in console application."""
    return "\033[1m" + text + "\033[0m"


def clear_directory(directory):
    """Remove files and folders, so that the directory becomes empty (except for hidden files)."""
    if not os.path.exists(directory):
        print("(The folder does not exist; it will be created.)")
        os.makedirs(directory, exist_ok=True)
        return True

    old_files = []
    old_dirs = []
    with os.scandir(directory) as it:
        for entry in it:
            if not entry.name.startswith(".") and entry.is_file():
                old_files.append(entry)
            elif entry.is_dir():
                old_dirs.append(entry)
    if not old_files and not old_dirs:
        return True

    max_tries = 5
    k = 0
    while k < max_tries:
        print(
            "Folder already exists! Do you want to clean it up (existing content will be removed)? (y/n)",
            end=" ",
        )
        answer = input()
        if answer == "n":
            return False
        elif answer == "y":
            try:
                for entry in old_files:
                    os.remove(entry)
                for entry in old_dirs:
                    shutil.rmtree(entry)
            except:
                print(
                    "Something wrong happened when cleaning the folder (maybe some files are locked by other application?)!"
                )
                return False
            return True
        k += 1
    return False


def get_calib_status(calib_core_id):
    """Return the status of a single calibration."""
    try:
        response = jinko.makeRequest(
            path=f"/core/v2/calibration_manager/calibration/{calib_core_id['id']}/snapshots/{calib_core_id['snapshotId']}/status",
            method="GET",
        )
        return response.json()
    except requests.exceptions.HTTPError:
        return ""
