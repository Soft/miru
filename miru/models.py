# Miru is a tool for maintaining a log of seen tv-series' episodes.
# Copyright (C) 2011-2019 Samuel Laurén <samuel.lauren@iki.fi>

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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Enum

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
            if self.status:
                self.status = None

    def remove_view(self):
        if self.seen > 0:
            self.seen -= 1
