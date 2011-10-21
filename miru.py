#!/usr/bin/env python2

import urwid
import os.path
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Enum, create_engine, and_, func

DEFAULT_DATABASE = os.path.expanduser("~/.miru.db")

class MainWindow(object):
	palette = [
			("body", "default", "default"),
			("reveal focus", "black", "white"),
			("current", "white", "dark blue"),
			("completed", "white", "dark green"),
			("hold", "white", "dark cyan"),
			("dropped", "white", "dark gray"),
			("planned", "white", "dark red"),
			("highlight", "black", "white")
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
		self.session = session
		self.display_view(self.current)
	
	def unhandled_input(self, key):
		if key in ("q", "Q"):
			raise urwid.ExitMainLoop()
		elif key == "h":
			self.display_view(self.current - 1 if (self.current - 1) >= 0 else len(self.views) - 1)
		elif key == "l":
			self.display_view(self.current + 1 if (self.current + 1) <= len(self.views) - 1 else 0)
		elif key in map(str, range(1, len(self.views) + 1)):
			self.display_view(int(key) - 1)
		elif key == "n":
			dialog = AddSeriesDialog(self.views[self.current], self.session)
			urwid.connect_signal(dialog, "closed", self.add_series_dialog_closed)
			self.frame.set_body(dialog)
	
	def add_series_dialog_closed(self):
		self.display_view(self.current)
	
	def display_view(self, index):
		self.current = index
		self.views[index].reload()
		self.set_terminal_title("Miru - %s" % self.views[index].title)
		if self.frame:
			self.frame.set_body(self.views[index])
		else:
			self.frame = urwid.Frame(self.views[index])

	def set_terminal_title(self, title):
		import sys
		sys.stdout.write("\x1b]2;%s\x07" % title)

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
		urwid.connect_signal(self.walker, "series_changed", self.redraw_footer)
		urwid.connect_signal(self.walker, "marking_activated", self.marking_activated)
		urwid.connect_signal(self.walker, "marking_deactivated", self.redraw_footer)
		urwid.connect_signal(self.walker, "deletion_requested", self.handle_delete)
		urwid.connect_signal(self.walker, "setting_seen_requested", self.handle_set_seen)
		self.table = SeriesTable(self.walker)
		self.setup_widgets()
		urwid.WidgetWrap.__init__(self, urwid.Frame(self.body, self.header, self.footer))
		self.reload()
	
	def marking_activated(self):
		self.footer = urwid.AttrWrap(
			urwid.Text([("highlight", "Mark as:"), " ",
				("highlight", "a"), "ctive, ",
				"on ", ("highlight", "h"), "old, ",
				("highlight", "d"), "ropped, ",
				("highlight", "p"), "lanned"], "left"),
			self.attr)
		self.refresh()

	def redraw_footer(self):
		self._w.set_focus("body")
		self.setup_footer()
		self.refresh()

	def show_input(self, widget, callback, *args):
		def wrapper(*signal_args):
			self._w.set_focus("body")
			return callback(*(signal_args + args))
		urwid.connect_signal(widget, "input_received", wrapper)
		urwid.connect_signal(widget, "input_cancelled", self.redraw_footer)
		self.footer = urwid.AttrWrap(widget, self.attr)
		self._w.set_focus("footer")
		self.refresh()
	
	def handle_delete(self, series):
		self.show_input(Prompt(u"Do you really want to delete \"%s\" [y/N]?: " % series.name),
				self.delete_confirmation, series)
	
	def delete_confirmation(self, text, series):
		if text.lower() == u"y":
			self.session.delete(series)
			self.session.commit()
			self.reload()
		else:
			self.redraw_footer()
	
	def handle_set_seen(self, series):
		self.show_input(IntPrompt(u"Set the number of seen episodes for \"%s\": " % series.name),
				self.set_seen_confirmation, series)
	
	def set_seen_confirmation(self, number, series):
		series.seen = number if number <= series.episodes else series.episodes
		self.session.commit()
		self.reload()
	
	def refresh(self):
		self._w.set_body(self.body)
		self._w.set_header(self.header)
		self._w.set_footer(self.footer)
	
	def reload(self):
		self.walker.reload()
		self.refresh()
	
	def setup_header(self):
		self.header = urwid.AttrWrap(urwid.Text(self.title, "center"), self.attr)
	
	def setup_body(self):
		self.body = urwid.AttrWrap(urwid.Pile([
				("flow", urwid.Divider(u" ")),
				self.table
			], focus_item=1), "body")
	
	def setup_footer(self):
		self.footer = urwid.AttrWrap(
				urwid.Text(u"Total of %d seen episodes" % self.walker.total_seen_episodes, "center"),
				self.attr
			)
	
	def setup_widgets(self):
		self.setup_header()
		self.setup_body()
		self.setup_footer()

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

class SeriesWalker(object):
	def __init__(self, session, filter):
		self.session = session
		self.filter = filter
		self.focus = 0
		self.reload()
	
	def reload(self):
		self.data = self.session.query(Series).filter(self.filter).order_by(Series.name).all()
		self.entries = [urwid.AttrMap(w, None, "reveal focus") for w in map(self._create_entry, self.data)]
		urwid.emit_signal(self, "series_changed")
	
	def _create_entry(self, series):
		entry = SeriesEntry(self.session, series) 
		urwid.connect_signal(entry, "series_changed", self.reload)
		re_emit = ("marking_activated", "marking_deactivated", "deletion_requested", "setting_seen_requested")
		for signal in re_emit:
			urwid.connect_signal(entry, signal, self.re_emit, signal)
		return entry

	def _clamp_focus(self):
		if self.focus >= len(self.entries):
			self.focus = len(self.entries) - 1
	
	def get_focus(self):
		if len(self.entries) == 0:
			return (None, None)
		self._clamp_focus()
		return (self.entries[self.focus], self.focus)

	def get_next(self, position):
		next_position = position + 1
		if len(self.entries) <= next_position:
			return (None, None)
		return (self.entries[next_position], next_position)

	def get_prev(self, position):
		prev_position = position - 1
		if prev_position < 0:
			return (None, None)
		return self.entries[prev_position], prev_position

	def set_focus(self, position):
		self.focus = position
	
	def re_emit(self, *args):
		if len(args) >= 2:
			urwid.emit_signal(self, args[-1], *args[0:-1])
		else:
			urwid.emit_signal(self, args[-1])
	
	@property
	def total_seen_episodes(self):
		return self.session.query(func.sum(Series.seen)).filter(self.filter).one()[0] or 0

urwid.register_signal(SeriesWalker, ["series_changed", "marking_activated", "marking_deactivated",
	"deletion_requested", "setting_seen_requested"])

class SeriesEntry(urwid.WidgetWrap):
	__marking_active = False

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

	def handle_marking(self, key):
		keys = {
				"a": None, # mark as active
				"h": "hold", # mark as on hold
				"d": "dropped", # mark as dropped
				"p": "planned" # mark as planned
			}
		self.__marking_active = False
		urwid.emit_signal(self, "marking_deactivated")
		if key in keys.keys():
			self.series.status = keys[key]
			self.session.commit()
			urwid.emit_signal(self, "series_changed")
		else:
			return key
	
	def keypress(self, size, key):
		if self.__marking_active:
			return self.handle_marking(key)
		if key in ("i", "d"):
			if key == "i":
				self.series.add_view()
			else:
				self.series.remove_view()
			self.session.commit() # Maybe we should commit only after some time
			urwid.emit_signal(self, "series_changed")
		elif key == "m":
			urwid.emit_signal(self, "marking_activated")
			self.__marking_active = True
		elif key == "s":
			urwid.emit_signal(self, "setting_seen_requested", self.series)
		elif key == "x":
			urwid.emit_signal(self, "deletion_requested", self.series)
		else:
			return key

urwid.register_signal(SeriesEntry, ["series_changed", "marking_activated", "marking_deactivated",
	"deletion_requested", "setting_seen_requested"])

class VimStyleListBox(urwid.ListBox):
	""" ListBox that changes focus with j and k keys and supports mouse wheel scrolling"""

	def keypress(self, size, key):
		if key == "k":
			return self._keypress_up(size)
		elif key == "j":
			return self._keypress_down(size)
		else:
			return urwid.ListBox.keypress(self, size, key)
	
	def mouse_event(self, size, event, button, col, row, focus):
		if button == 4: # Scroll wheel up
			self._keypress_up(size)
			return True
		elif button == 5: # Scroll wheel down
			self._keypress_down(size)
			return True
		else:
			return False

class Prompt(urwid.Edit):
	def format(self, string):
		return string

	def keypress(self, size, key):
		if key == "enter":
			urwid.emit_signal(self, "input_received", self.format(self.get_edit_text()))
		elif key == "esc":
			urwid.emit_signal(self, "input_cancelled")
		else:
			urwid.Edit.keypress(self, size, key)

urwid.register_signal(Prompt, ["input_received", "input_cancelled"])

class IntPrompt(Prompt):
	def format(self, string):
		return int(string) if string else 0

	def valid_char(self, char):
		return len(char) == 1 and char in "0123456789"

urwid.register_signal(IntPrompt, ["input_received", "input_cancelled"]) # Do I really have to specify this

class AddSeriesDialog(urwid.Overlay):
	selected = 0

	def __init__(self, background, session):
		self.session = session
		self.name_edit = urwid.Edit()
		self.episode_edit = urwid.IntEdit()
		self.add_button = urwid.Button(u"Add", self.add_button_click)
		self.tab_index = [self.name_edit, self.episode_edit, self.add_button]
		self.content = urwid.GridFlow([
				urwid.Text(u"Name"),
				self.name_edit,
				urwid.Text(u"Episodes"),
				self.episode_edit,
				self.add_button
			], 20, 1, 1, "center")
		linebox = urwid.LineBox(urwid.Filler(self.content), u"Add Series")
		self.select()
		urwid.Overlay.__init__(self, linebox, background, "center", 50, "middle", 15)
	
	def select(self):
		self.content.set_focus(self.tab_index[self.selected])
	
	def add_button_click(self, widget):
		self.add_series(self.name_edit.get_edit_text(), 0, self.episode_edit.get_edit_text())
		urwid.emit_signal(self, "closed")
	
	def keypress(self, size, key):
		if key == "tab":
			self.selected = (self.selected + 1) % len(self.tab_index)
			self.select()
			return None
		if key == "esc":
			urwid.emit_signal(self, "closed")
			return None
		else:
			return urwid.Overlay.keypress(self, size, key)
	
	def add_series(self, name, seen, episodes, status=None):
		self.session.add(Series(name=name, episodes=episodes, seen=seen, status=status))
		self.session.commit()

urwid.register_signal(AddSeriesDialog, ["closed"])

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
		n\t: Add new series
		x\t: Delete selected series
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

if __name__ == "__main__":
	main()



