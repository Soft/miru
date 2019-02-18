#!/usr/bin/env python3

from setuptools import setup

setup(
    name="miru",
    version="0.2.0",
    description="Utility for keeping track of watched TV episodes and movies.",
    author="Samuel Laurén",
    author_email="samuel.lauren@iki.fi",
    url="https://soft.github.io/miru/",
    packages=["miru"],
    entry_points={"console_scripts": ["miru=miru.app:main"]},
    install_requires=["urwid", "sqlalchemy"],
    classifiers=[
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Environment :: Console :: Curses",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
    ],
    keywords=["log", "management", "tv"],
)
