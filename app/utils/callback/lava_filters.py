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
    r'\<LAVA_SIGNAL_.+>')


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
