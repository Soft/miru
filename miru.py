#!/usr/bin/env python2

import urwid
import os.path
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Enum, create_engine, and_, func

class MainWindow(object):
	palette = [
			("body", "default", "default"),
			("reveal focus", "black", "white"),
			("current", "white", "dark blue"),
			("completed", "white", "dark green"),
			("hold", "white", "dark cyan"),
			("dropped", "white", "dark gray"),
			("planned", "white", "dark red")
		]
	frame = None

	def __init__(self, session):
		self.views = [
				View("Currently Watching", "current", session, and_(Series.seen < Series.episodes, Series.status == None)),
				View("Completed", "completed", session, Series.seen == Series.episodes),
				View("On Hold", "hold", session, Series.status == "hold"),
				View("Dropped", "dropped", session, Series.status == "dropped"),
				View("Plan to Watch", "planned", session, Series.status == "planned"),
			]
		self.current = 0
		self.display_view(self.current)
	
	def unhandled_input(self, key):
		if key in ("q", "Q"):
			raise urwid.ExitMainLoop()
		elif key == "h":
			self.display_view(self.current - 1 if (self.current - 1) >= 0 else len(self.views) - 1)
		elif key == "l":
			self.display_view(self.current + 1 if (self.current + 1) <= len(self.views) - 1 else 0)
		elif key == "n":
			pass # Add new series to the current view
	
	def display_view(self, index):
		self.current = index
		if self.frame:
			self.frame.set_body(self.views[index])
		else:
			self.frame = urwid.Frame(self.views[index])

	def main(self):
		self.loop = urwid.MainLoop(self.frame,
				self.palette,
				unhandled_input=self.unhandled_input)
		self.loop.run()

class View(urwid.WidgetWrap):
	def __init__(self, title, attr, session, filter):
		self.title = title
		self.attr = attr
		self.session = session
		self.filter = filter
		self.walker = SeriesWalker(session, filter)
		urwid.connect_signal(self.walker, "series_changed", self.refresh)
		self.table = SeriesTable(self.walker)
		self.refresh()
	
	def refresh(self): # ugly
		header = urwid.AttrWrap(urwid.Text(self.title, "center"), self.attr)
		body = urwid.AttrWrap(urwid.Pile([
				("flow", urwid.Divider(u" ")),
				self.table
			], focus_item=1), "body")
		footer = urwid.AttrWrap(
				urwid.Text(u"Total of %d seen episodes" % self.walker.total_seen_episodes, "center"),
				"footer"
			)
		if not hasattr(self, "_wrapped_widget"): # ugly
			urwid.WidgetWrap.__init__(self, urwid.Frame(body, header, footer))
		else:
			self._w.set_body(body)
			self._w.set_header(header)
			self._w.set_footer(footer)

class DataTable(urwid.Pile):
	def __init__(self, columns, walker):
		self.list_box = VimStyleListBox(walker)
		urwid.Pile.__init__(self, [
				("flow", urwid.Columns(columns)),
				("flow", urwid.Divider(u"\u2500")),
				self.list_box
			], focus_item=2)

class SeriesTable(DataTable):
	def __init__(self, walker):
		self.walker = walker
		DataTable.__init__(self, [
				("weight", 0.6, urwid.Text(u"Name")),
				("weight", 0.2, urwid.Text(u"Seen", align="right")),
				("weight", 0.2, urwid.Text(u"Total", align="right")),
			], walker)
	
class SeriesWalker(urwid.SimpleListWalker):
	def __init__(self, session, filter):
		self.session = session
		self.filter = filter
		query = session.query(Series).filter(filter).order_by(Series.name)
		urwid.SimpleListWalker.__init__(self, [urwid.AttrMap(w, None, "reveal focus") for w in map(self.create_entry, query)])
		
	def create_entry(self, series):
		entry = SeriesEntry(self.session, series) 
		urwid.connect_signal(entry, "series_changed", self.refresh)
		return entry

	@property
	def total_seen_episodes(self):
		return self.session.query(func.sum(Series.seen)).filter(self.filter).one()[0] or 0

	def refresh(self):
		urwid.emit_signal(self, "series_changed")

urwid.register_signal(SeriesWalker, ["series_changed"])

class SeriesEntry(urwid.WidgetWrap):
	# Not sure if it's a good idea to spread references to session and Series objects around like this...
	def __init__(self, session, series):
		self.session = session
		self.series = series
		self.name = urwid.Text(self.series.name)
		self.seen = urwid.Text(unicode(self.series.seen), align="right")
		self.episodes = urwid.Text(unicode(self.series.episodes), align="right")
		urwid.WidgetWrap.__init__(self, urwid.Columns([
				("weight", 0.6, self.name),
				("weight", 0.2, self.seen),
				("weight", 0.2, self.episodes),
			]))
	
	def selectable(self):
		return True
	
	def keypress(self, size, key):
		if key in ("i", "d"):
			if key == "i":
				self.series.add_view()
			else:
				self.series.remove_view()
			self.session.commit() # Maybe we should commit only after some time
			self.refresh()
			urwid.emit_signal(self, "series_changed")
		elif key == "s":
			pass # Set seen to an arbitary number
		elif key == "x":
			pass # Remove series
		else:
			return key
	
	def refresh(self):
		self.name.set_text(self.series.name)
		self.seen.set_text(unicode(self.series.seen))
		self.episodes.set_text(unicode(self.series.episodes))

# This is probably a wrong place to register these
urwid.register_signal(SeriesEntry, ["series_changed"])

class VimStyleListBox(urwid.ListBox):
	""" ListBox that changes focus with j and k keys """

	def keypress(self, size, key):
		if key == "k":
			return self._keypress_up(size)
		elif key == "j":
			return self._keypress_down(size)
		else:
			return urwid.ListBox.keypress(self, size, key)

class Dialog(urwid.WidgetWrap):
	pass

Base = declarative_base()

class Series(Base):
	__tablename__ = "series"
	id = Column(Integer, primary_key=True)
	name = Column(String(64), nullable=False)
	episodes = Column(Integer, default=1)
	seen = Column(Integer, default=0)
	added = Column(DateTime())
	completed = Column(DateTime())
	status = Column(Enum("hold", "dropped", "planned"))

	def add_view(self):
		if self.episodes > self.seen:
			self.seen += 1
	
	def remove_view(self):
		if self.seen > 0:
			self.seen -= 1

def parse_args():
	from textwrap import dedent
	keys = dedent("""
		Keys
		h: Move to a view in left
		l: Move to a view in right
		j: Focus next item
		k: Focus previous item
		i: Increment seen episodes count for selected series
		d: Decrement seen episodes count for selected series
		s: Set seen episodes count to an arbitary number
		n: Add new series
		x: Delete selected series
	""")
	parser = ArgumentParser("Tool for maintaining a log of seen tv-series' episodes.",
			epilog=keys,
			formatter_class=RawDescriptionHelpFormatter)
	parser.add_argument("-m", "--memory", action="store_true", help="Use temporary in-memory database")
	parser.add_argument("-d", "--database", default=os.path.expanduser("~/.episodes"), help="Path to a database")
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

if __name__ == "__main__":
	main()



