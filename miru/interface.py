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

import urwid
import sys

from sqlalchemy import and_, func

from miru.models import Series

class MainWindow(object):
	palette = [
			("body", "default", "default"),
			("reveal focus", "black", "white"),
			("current", "white", "dark blue"),
			("completed", "white", "dark green"),
			("hold", "white", "dark cyan"),
			("dropped", "white", "dark gray"),
			("planned", "white", "dark red"),
			("highlight", "black", "white"),
			("edit", "white", "dark gray"),
			("button", "white", "dark blue"),
			("dialog", "black", "light gray")
		]
	frame = None

	def __init__(self, session):
		self.views = [
				View("Currently Watching", "current", None, session, and_(Series.seen < Series.episodes, Series.status == None)),
				View("Completed", "completed", "completed", session, Series.seen == Series.episodes), # ugly
				View("On Hold", "hold", "hold", session, Series.status == "hold"),
				View("Dropped", "dropped", "dropped", session, Series.status == "dropped"),
				View("Plan to Watch", "planned", "planned", session, Series.status == "planned"),
			]
		for view in self.views:
			urwid.connect_signal(view, "ordering_changed", self.ordering_changed)
		self.current = 0
		self.session = session
		self.display_view(self.current)
	
	def unhandled_input(self, key):
		if key in ("q", "Q"):
			raise urwid.ExitMainLoop()
		elif not self.displaying_dialog:
			if key in ("h", "left"):
				self.display_view(self.current - 1 if (self.current - 1) >= 0 else len(self.views) - 1)
			elif key in ("l", "right"):
				self.display_view(self.current + 1 if (self.current + 1) <= len(self.views) - 1 else 0)
			elif key in map(str, range(1, len(self.views) + 1)):
				self.display_view(int(key) - 1)
			elif key == "a":
				self.show_add_series_dialog()
	
	def show_add_series_dialog(self):
		dialog = AddSeriesDialog(self.views[self.current], self.views[self.current].status, self.session)
		urwid.connect_signal(dialog, "closed", self.add_series_dialog_closed)
		self.frame.set_body(dialog)
	
	def add_series_dialog_closed(self):
		self.display_view(self.current)
	
	def ordering_changed(self, ordering):
		for view in self.views:
			view.set_ordering(ordering)
		self.views[self.current].reload()
	
	def display_view(self, index):
		self.current = index
		self.views[index].reload()
		self.set_terminal_title("Miru - %s" % self.views[index].title)
		if self.frame:
			self.frame.set_body(self.views[index])
		else:
			self.frame = urwid.Frame(self.views[index])
	
	@property
	def displaying_dialog(self):
		return isinstance(self.frame.get_body(), AddSeriesDialog)

	def set_terminal_title(self, title):
		sys.stdout.write("\x1b]2;%s\x07" % title)

	def main(self):
		self.loop = urwid.MainLoop(self.frame,
				self.palette,
				unhandled_input=self.unhandled_input)
		self.loop.run()

class View(urwid.WidgetWrap):
	signals = ["ordering_changed"]

	__order_by_active = False

	def __init__(self, title, attr, status, session, filter):
		self.title = title
		self.attr = attr
		self.status = status
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
	
	def order_by_activated(self):
		self.footer = urwid.AttrWrap(
			urwid.Text([("highlight", "Order by:"), " ",
				("highlight", "n"), "ame, ",
				("highlight", "s"), "een, ",
				("highlight", "e"), "pisodes"], "left"),
			self.attr)
		self.refresh()
	
	def handle_order_by(self, key):
		keys = {
				"n": Series.name,
				"s": Series.seen,
				"e": Series.episodes
			}
		self.__order_by_active = False
		self.redraw_footer()
		if key in keys.keys():
			urwid.emit_signal(self, "ordering_changed", keys[key])
		else:
			return key

	def redraw_footer(self):
		self._w.set_focus("body")
		self.setup_footer()
		self.refresh()
	
	def keypress(self, size, key):
		if self.__order_by_active:
			return self.handle_order_by(key)
		elif key == "o":
			self.__order_by_active = True
			self.order_by_activated()
		else:
			return self._w.keypress(size, key)

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
	
	def set_ordering(self, ordering):
		self.walker.order_by = ordering
	
	def setup_header(self):
		self.header = urwid.AttrWrap(
			urwid.Columns([
					("weight", 0.1, urwid.Text("<")),
					urwid.Text(self.title, "center"),
					("weight", 0.1, urwid.Text(">", "right"))
				]),
			self.attr)
	
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
		self.order_by = Series.name
		self.focus = 0
		self.reload()
	
	def reload(self):
		self.data = self.session.query(Series).filter(self.filter).order_by(self.order_by).all()
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
	signals = ["series_changed", "marking_activated", "marking_deactivated",
	"deletion_requested", "setting_seen_requested"]

	__marking_active = False

	def __init__(self, session, series):
		self.session = session
		self.series = series
		self.name = urwid.Text(self.series.name, wrap="clip")
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
	signals = ["input_received", "input_cancelled"]

	def format(self, string):
		return string

	def keypress(self, size, key):
		if key == "enter":
			urwid.emit_signal(self, "input_received", self.format(self.get_edit_text()))
		elif key == "esc":
			urwid.emit_signal(self, "input_cancelled")
		else:
			urwid.Edit.keypress(self, size, key)

class IntPrompt(Prompt):
	def format(self, string):
		return int(string) if string else 0

	def valid_char(self, char):
		return len(char) == 1 and char in "0123456789"

class AddSeriesDialog(urwid.Overlay):
	signals = ["closed"]
	selected = 0

	def __init__(self, background, status, session):
		self.session = session
		self.status = status
		self.name_edit = urwid.AttrWrap(urwid.Edit(), "edit")
		self.episode_edit = urwid.AttrWrap(urwid.IntEdit(), "edit")
		self.add_button = urwid.AttrWrap(urwid.Button(u"Add", self.add_button_click), "button")
		self.tab_index = [self.name_edit, self.episode_edit, self.add_button]
		self.content = urwid.GridFlow([
				urwid.Text(u"Name"),
				self.name_edit,
				urwid.Text(u"Episodes"),
				self.episode_edit,
				self.add_button
			], 20, 1, 1, "center")
		linebox = urwid.AttrWrap(urwid.LineBox(urwid.Filler(self.content), u"Add Series"), "dialog")
		self.select()
		urwid.Overlay.__init__(self, linebox, background, "center", 50, "middle", 12)
	
	def select(self):
		self.content.set_focus(self.tab_index[self.selected])
	
	def add_button_click(self, widget):
		self.add_series(self.name_edit.get_edit_text(), 0, self.episode_edit.get_edit_text())
		urwid.emit_signal(self, "closed")
	
	def keypress(self, size, key):
		if key == "tab":
			self.selected = (self.selected + 1) % len(self.tab_index)
			self.select()
		if key == "esc":
			urwid.emit_signal(self, "closed")
		else:
			return urwid.Overlay.keypress(self, size, key)
	
	def add_series(self, name, seen, episodes):
		seen = episodes if self.status == "completed" else seen
		status = None if self.status in (None, "completed") else self.status
		self.session.add(Series(name=name, episodes=episodes, seen=seen, status=status))
		self.session.commit()


