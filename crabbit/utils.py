"""Utility functions used in the crabbit package."""

__all__ = [
    "bold_text",
    "clear_directory",
]

import shutil
import os
import re
import json
import requests
import jinko_helpers as jinko


def bold_text(text: str) -> str:
    """Return bold text to print in console application."""
    return "\033[1m" + text + "\033[0m"


def clear_directory(directory: str, force: bool) -> None:
    """Remove files and folders, so that the directory becomes empty (except for hidden files)."""
    if not os.path.exists(directory):
        if not force:
            print(f"(The folder {directory} does not exist; it will be created.)")
        os.makedirs(directory, exist_ok=True)
        return True

    old_files = []
    old_dirs = []
    try:
        with os.scandir(directory) as it:
            for entry in it:
                if not entry.name.startswith(".") and entry.is_file():
                    old_files.append(entry)
                elif entry.is_dir():
                    old_dirs.append(entry)
    except NotADirectoryError:
        print("Error: the output path is not a folder")
        return False
    if not old_files and not old_dirs:
        return True

    max_tries = 5
    k = 0
    while k < max_tries:
        answer = "y"
        if not force:
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


def check_project_item_url(url):
    """Get the project item from URL or print a nice error message."""
    message = f'{bold_text("Error:")} {url} is not a valid project item URL!'
    sid, revision = jinko.get_sid_revision_from_url(url)
    if sid is None:
        print(message)
        return None
    try:
        project_item = jinko.get_project_item(sid=sid, revision=revision)
    except requests.exceptions.HTTPError:
        print(message)
        return None
    if "type" not in project_item:
        print(message)
        return None
    return project_item


def parse_jsonc(jsonc_path):
    """Parse commented JSON format"""
    # based on: https://github.com/NickolaiBeloguzov/jsonc-parser/tree/master
    regex = re.compile(
        r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)", re.MULTILINE | re.DOTALL
    )
    json_file = open(jsonc_path, "r")
    data_raw = json_file.read()
    json_file.close()

    def __re_sub(match):
        if match.group(2) is not None:
            return ""
        else:
            return match.group(1)

    try:
        data = regex.sub(__re_sub, data_raw)
        return True, json.loads(regex.sub(__re_sub, data))
    except Exception as e:
        return False, {}
