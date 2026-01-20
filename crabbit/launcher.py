"""Crabbit app launcher module."""

__all__ = ["CrabbitAppLauncher"]

import os

import jinko_helpers as jinko
import crabbit.download as download
import crabbit.merge as merge
from crabbit.utils import check_project_item_url


class CrabbitAppLauncher:
    """Crabbit app launcher, connecting argparse to cli apps (and gui apps in the future)."""

    def __init__(self):
        self.mode = ""
        self.input = None
        self.output = ""
        self.force = False
        self.csv = ""

    def run(self):
        self.output = os.path.abspath(self.output)
        try:
            jinko.initialize()
        except:
            return

        if self.mode == "download":
            project_item = check_project_item_url(self.input[0])
            if project_item is None:
                return
            crab = download.CrabbitDownloader(
                project_item, self.output, self.csv, self.force
            )
            print(
                f'Downloading jinko project item "{self.input[0]}" to {self.output}\n',
            )
            crab.run()
        elif self.mode == "merge":
            if not self.input:
                print("Error:\nThe input path is not valid!", "\n")
                return False
            crab = merge.CrabbitMerger(self.input, self.output)
            crab.run()
        else:
            print(f'The mode "{self.mode}" is still under development!')
