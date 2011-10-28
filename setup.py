# coding: utf-8
from setuptools import setup

setup(name="miru",
	version="0.1.0",
	description="Tool for maintaining a log of seen tv-series' episodes.",
	author="Samuel Laurén",
	author_email="samuel.lauren@iki.fi",
	url="https://bitbucket.org/Soft/miru",
	license="GPL 3",
	packages=["miru"],
	scripts=["scripts/miru"],
	install_requires=["urwid>=1.0.0", "sqlalchemy>=0.7.2"],
	classifiers=[
		"Intended Audience :: End Users/Desktop",
		"License :: OSI Approved :: GNU General Public License (GPL)",
		"Environment :: Console :: Curses",
		"Operating System :: POSIX",
		"Programming Language :: Python :: 2.7",
		"Topic :: Utilities"
		],
	keywords=["log", "management", "tv"]
	)

