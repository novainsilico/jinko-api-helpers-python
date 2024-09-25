import argparse

from crabbit import launcher
from crabbit.utils import bold_text


def get_usage():
    """Show usage of the "crabbit" app."""
    return (
        bold_text("python -m crabbit {mode} {URL} {path}")
        + f"\n\nexample: {bold_text('python -m crabbit download https://jinko.ai/my-project-item my-project/download-folder')}"
    )


# parse the command line arguments
parser = argparse.ArgumentParser(usage=get_usage())
parser.add_argument(
    "mode",
    choices=["download", "launch"],
    help='The running mode of crabbit: currently only "download" mode is available.',
)
parser.add_argument("url", help="URL of the jinko project item or jinko folder.")
parser.add_argument(
    "path",
    help="Path to the local working folder of crabbit, e.g. folder for downloading the results of a trial.",
)
crab = launcher.CrabbitAppLauncher()
parser.parse_args(namespace=crab)

# run the app launcher
crab.run()
