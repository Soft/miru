# Miru 📺

[![GitHub release](https://img.shields.io/github/release/Soft/miru.svg)](https://github.com/Soft/miru/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

**見る — to watch; to view;**

Utility for keeping track of watched TV episodes and movies. Includes a nice
ncurses based interface and SQLite backend for storage.

![screenshot](https://raw.githubusercontent.com/Soft/miru/master/docs/screenshots/shot-4.png)

# Installation

```
pip install --user git+https://github.com/Soft/miru.git
```

# Key bindings

Key | Action
--- | ---
`h`, `←` | Move to a view in left
`l`, `→` | Move to a view in right
`1` — `5` | Move to a spesific view
`j`, `↓` | Focus next item
`k`, `↑` | Focus previous item
`i` | Increment seen episodes count for selected series
`d` | Decrement seen episodes count for selected series
`s` | Set seen episodes count to an arbitrary number
`m` `a` | Mark series as active
`m` `h` | Mark series as on hold
`m` `d` | Mark series as dropped
`m` `p` | Mark series as planned
`o` `n` | Order by name
`o` `s` | Order by seen episodes
`o` `e` | Order by episode count
`a` | Add new series
`x` | Delete selected series
`q`, `Q` | Exit Miru
