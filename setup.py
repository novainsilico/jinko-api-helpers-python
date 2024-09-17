from setuptools import setup, find_packages


# Dynamically load the version from jinko/__version__.py
def read_version():
    version = {}
    with open("jinko_helpers/__version__.py") as fp:
        exec(fp.read(), version)
    return version["__version__"]


setup(
    name="jinko",
    version=read_version(),
    packages=find_packages(),
    install_requires=[
        "requests",
        "pandas",
    ],
    url="https://github.com/novainsilico/jinko-api-helpers-python",
    author="Nova In Silico",
    author_email="oss@novainsilico.ai",
    description="Python helpers function to ease use of Jinko's API",
)
