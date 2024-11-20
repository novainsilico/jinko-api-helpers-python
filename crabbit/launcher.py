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
        self.input = None
        self.output = ""

    def run(self):
        self.output = os.path.abspath(self.output)
        try:
            jinko.initialize()
        except:
            return

        if self.mode == "download":
            project_item = self.check_project_item_url()
            if project_item is None:
                return
            crab = cli.CrabbitDownloader(project_item, self.output)
            print(
                "Downloading jinko project item",
                self.input,
                "to",
                self.output,
                end="\n\n",
            )
            if clear_directory(self.output):
                crab.run()
        elif self.mode == "merge":
            if not self.input:
                print("Error:\nThe input path is not valid!", "\n")
                return False
            crab = cli.CrabbitMerger(self.input, self.output)
            crab.run()
        else:
            print(f'The mode "{self.mode}" is still under development!')

    def check_project_item_url(self):
        """Get the project item from URL or print a nice error message."""
        message = f'{bold_text("Error:")} {self.input} is not a valid project item URL!'
        sid, revision = get_sid_revision_from_url(self.input[0])
        if sid is None:
            print(message)
            return None
        try:
            project_item = jinko.get_project_item(sid, revision)
        except requests.exceptions.HTTPError:
            print(message)
            return None
        return project_item
