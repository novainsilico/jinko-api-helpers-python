"""Crabbit app launcher module."""

__all__ = ["CrabbitAppLauncher"]

import os
import requests

import jinko_helpers as jinko
import crabbit.cli as cli
from crabbit.utils import bold_text, clear_directory, get_sid_revision_from_url


class CrabbitAppLauncher:
    """Crabbit app launcher, connecting argparse to cli apps (and gui apps in the future)."""

    def __init__(self):
        self.mode = ""
        self.url = ""
        self.path = ""

    def run(self):
        self.path = os.path.abspath(self.path)
        try:
            jinko.initialize()
        except:
            return

        if self.mode == "download":
            project_item = self.check_project_item_url()
            if project_item is None:
                return
            crab = cli.CrabbitDownloader(project_item, self.path)
            print(
                "Downloading jinko project item", self.url, "to", self.path, end="\n\n"
            )
            if clear_directory(self.path):
                crab.run()
        else:
            print(f'The mode "{self.mode}" is still under development!')

    def check_project_item_url(self):
        """Get the project item from URL or print a nice error message."""
        message = f'{bold_text("Error:")} {self.url} is not a valid project item URL!'
        sid, revision = get_sid_revision_from_url(self.url)
        if sid is None:
            print(message)
            return None
        try:
            project_item = jinko.getProjectItem(sid, revision)
        except requests.exceptions.HTTPError:
            print(message)
            return None
        return project_item
