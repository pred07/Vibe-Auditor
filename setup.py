from setuptools import setup, find_packages

setup(
    name="audit-watch",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "watchdog>=3.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "openpyxl>=3.1.0",
        "pandas>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "audit=audit.cli:main",
            "audit-watch=audit.cli:watch",
        ],
    },
)
