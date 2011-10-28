# coding: utf-8
# Miru is a tool for maintaining a log of seen tv-series' episodes.
# Copyright (C) 2011 Samuel Laurén <samuel.lauren@iki.fi>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from miru.interface import MainWindow
from miru.models import Base, Series

DEFAULT_DATABASE = os.path.expanduser("~/.miru.db")

def parse_args():
	from textwrap import dedent
	keys = dedent("""
		Keys
		h\t: Move to a view in left
		l\t: Move to a view in right
		1-5\t: Move to a spesific view
		j\t: Focus next item
		k\t: Focus previous item
		i\t: Increment seen episodes count for selected series
		d\t: Decrement seen episodes count for selected series
		s\t: Set seen episodes count to an arbitrary number
		ma\t: Mark series as active
		mh\t: Mark series as on hold
		md\t: Mark series as dropped
		mp\t: Mark series as planned
		on\t: Order by name
		os\t: Order by seen episodes
		oe\t: Order by episode count
		a\t: Add new series
		x\t: Delete selected series
		q, Q\t: Exit Miru
	""")
	parser = ArgumentParser("Tool for maintaining a log of seen tv-series' episodes.",
			epilog=keys,
			formatter_class=RawDescriptionHelpFormatter)
	parser.add_argument("-m", "--memory", action="store_true", help="Use temporary in-memory database")
	parser.add_argument("-d", "--database", default=DEFAULT_DATABASE, help="Path to a database")
	return parser.parse_args()

def connect_database(path, memory=False):
	return create_engine("sqlite:///%s" % (":memory:" if memory else os.path.abspath(path)))

def main():
	args = parse_args()
	engine = connect_database(args.database, args.memory)
	Base.metadata.create_all(engine)
	Session = sessionmaker(engine)
	session = Session()
	MainWindow(session).main()


