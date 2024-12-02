import argparse

from crabbit import launcher
from crabbit.utils import bold_text


def get_usage():
    """Show usage of the "crabbit" app."""
    return (
        bold_text("python -m crabbit {mode} {input} {output}")
        + f"\n\nexample: {bold_text('python -m crabbit download https://jinko.ai/my-project-item my-project/download-folder')}"
    )


# parse the command line arguments
parser = argparse.ArgumentParser(usage=get_usage())
parser.add_argument(
    "mode",
    choices=["download", "merge"],
    help="The running mode of crabbit: (1) download (2) merge.",
)
parser.add_argument(
    "input",
    nargs="*",
    help="URL of the jinko project item or jinko folder, or local file paths.",
)
parser.add_argument(
    "output",
    help="Path to the output/path folder of crabbit, e.g. folder for downloading the results of a trial.",
)
parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    help="download: force cleaning the directory when downloading calibration best patient (not asking for confirmation).",
)

crab = launcher.CrabbitAppLauncher()
parser.parse_args(namespace=crab)

# run the app launcher
crab.run()
