#!/usr/bin/env python2

import urwid
from argparse import ArgumentParser
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Enum, create_engine, and_

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
		self.lists = [
				(("Currently Watching", "current"),
					SeriesTable(SeriesWalker(session, and_(Series.seen < Series.episodes, Series.status == None)))),
				(("Completed", "completed"),
					SeriesTable(SeriesWalker(session, Series.seen == Series.episodes))),
				(("On Hold", "hold"),
					SeriesTable(SeriesWalker(session, Series.status == "hold"))),
				(("Dropped", "dropped"),
					SeriesTable(SeriesWalker(session, Series.status == "dropped"))),
				(("Plan to Watch", "planned"),
					SeriesTable(SeriesWalker(session, Series.status == "planned")))
			]
		self.current = 0
		self.display_list(self.current)
	
	def unhandled_input(self, key):
		if key in ("q", "Q"):
			raise urwid.ExitMainLoop()
		elif key == "h":
			self.display_list(self.current - 1 if (self.current - 1) >= 0 else len(self.lists) - 1)
		elif key == "l":
			self.display_list(self.current + 1 if (self.current + 1) <= len(self.lists) - 1 else 0)
		elif key == "n":
			pass # Add new series to the current view
	
	def display_list(self, index):
		self.current = index
		header = urwid.AttrWrap(urwid.Text(self.lists[index][0][0], "center"), self.lists[index][0][1])
		body = urwid.AttrWrap(urwid.Pile([
				("flow", urwid.Divider(u" ")),
				self.lists[index][1]
			], focus_item=1), "body")
		footer = urwid.AttrWrap(
				urwid.Text(u"Total of %d seen episodes" % self.lists[index][1].total_seen_episodes, "center"),
				self.lists[index][0][1])
		if self.frame:
			self.frame.set_header(header)
			self.frame.set_body(body)
			self.frame.set_footer(footer)
		else:
			self.frame = urwid.Frame(body, header, footer)

	def main(self):
		self.loop = urwid.MainLoop(self.frame,
				self.palette,
				unhandled_input=self.unhandled_input)
		self.loop.run()
	
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
	
	@property
	def total_seen_episodes(self): # This really should be in SeriesWalker
		return self.walker.total_seen_episodes

class SeriesWalker(urwid.SimpleListWalker):
	def __init__(self, session, filter):
		self.session = session
		self.filter = filter
		self.total_seen_episodes = 0 # FIXME
		query = session.query(Series).filter(filter).order_by(Series.name)
		urwid.SimpleListWalker.__init__(self, [urwid.AttrMap(w, None, "reveal focus") for w in map(self.__create_entry, query)])
		
	def __create_entry(self, series):
		return SeriesEntry(self.session, series)

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
		if key == "i":
			self.series.add_view()
			self.session.commit() # Maybe we should commit only after some time
			self.refresh()
		elif key == "d":
			self.series.remove_view()
			self.session.commit()
			self.refresh()
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
	from os.path import expanduser
	parser = ArgumentParser("Tool for maintaining a log of seen tv-series' episodes.")
	parser.add_argument("-m", "--memory", action="store_true", help="Use temporary in-memory database")
	parser.add_argument("-d", "--database", default=expanduser("~/.episodes"), help="Path to a database")
	return parser.parse_args()

def connect_database(path, memory=False):
	return create_engine("sqlite:///%s" % (":memory:" if memory else path))

def main():
	args = parse_args()
	engine = connect_database(args.database, args.memory)
	Base.metadata.create_all(engine)
	Session = sessionmaker(engine)
	session = Session()
	MainWindow(session).main()

if __name__ == "__main__":
	main()



