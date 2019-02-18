#!/usr/bin/env python3

from setuptools import setup

setup(
    name="miru",
    version="0.2.0",
    description="Tool for maintaining a log of seen tv-series' episodes.",
    author="Samuel Laurén",
    author_email="samuel.lauren@iki.fi",
    url="https://bitbucket.org/Soft/miru",
    license="GPL 3",
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
