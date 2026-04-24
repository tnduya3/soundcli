#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="soundcli",
    version="0.1.0",
    description="A terminal-based SoundCloud music player with a responsive TUI",
    author="Nhat Duy",
    python_requires=">=3.11",
    packages=find_packages(),
    py_modules=["main", "app", "config", "models"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "soundcli=main:main_entry",
        ],
    },
    include_package_data=True,
)
