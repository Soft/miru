#!/usr/bin/env python3

from setuptools import setup, find_packages
from pathib import Path

readme = Path(__file__).parent.absolute() / "README.md"
long_description = readme.read_text()

setup(
    name="miru",
    version="0.2.0",
    description="Utility for keeping track of watched TV episodes and movies.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Samuel Laurén",
    author_email="samuel.lauren@iki.fi",
    url="https://soft.github.io/miru/",
    packages=find_packages(),
    entry_points={"console_scripts": ["miru=miru.app:main"]},
    install_requires=["urwid", "sqlalchemy"],
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Environment :: Console :: Curses",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
    ],
    keywords=["log", "management", "tv", "movies", "organizer", "collection"],
)
