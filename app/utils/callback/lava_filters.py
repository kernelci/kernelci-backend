# Copyright (C) Collabora Limited 2020
# Author: Michal Galka <michal.galka@collabora.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""
This module is meant to contain the lava log filtering functions.
These functions are used to filter out the content of the LAVA log when LAVA
callback is being processed.

Filtering functions should follow some rules:

- Name of the filtering function must start with `filter_`
- It can take only one argument which is a log line text to process
- It should return boolean value:
    - True - log line stays in the log
    - False - log line will be deleted

`LAVA_FILTERS` is a list of filtering functions (function objects)
and it gets automatically populated during module import.
"""

import re
import inspect


LAVA_SIGNAL_PATTERN = re.compile(
    r'^<LAVA_.+>')


def filter_log_levels(log_line):
    return log_line['lvl'] == 'target'


def filter_lava_signal(log_line):
    return not LAVA_SIGNAL_PATTERN.match(log_line['msg'])


def _get_lava_filters():
    filters = []
    for name, obj in globals().items():
        if name.startswith('filter') and inspect.isfunction(obj):
            filters.append(obj)
    return filters


LAVA_FILTERS = _get_lava_filters()
