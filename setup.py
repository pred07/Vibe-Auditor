from setuptools import setup, find_packages

setup(
    name="patchbuddy",
    version="1.0.3",
    packages=find_packages(),
    install_requires=[
        "watchdog",
        "click",
        "rich",
        "openpyxl",
        "pandas"
    ],
    entry_points={
        "console_scripts": [
            "audit=audit.cli:main",
            "patchbuddy=audit.cli:main"
        ]
    },
    author="0xbrijith",
    description="Your friendly patch companion",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/pred07/patchbuddy",
)
