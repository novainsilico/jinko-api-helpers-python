from setuptools import setup, find_packages

setup(
    name="jinko",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'requests',
        'pandas',
    ],
    url="https://github.com/novainsilico/jinko-api-helpers-python",
    author="Nova In Silico",
    author_email="oss@novainsilico.ai",
    description="Python helpers function to ease use of Jinko's API",
)
