#!/usr/bin/env python
# Copyright (C) Collabora Limited 2017,2018,2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
# Author: Guillaume Tucker <guillaume@mangoz.org>
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

import argparse
import cgi
import dateutil.parser
import json
import re
import yaml
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

HTML_HEAD = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head>
  <title>Boot log: {board}</title>
  <style type="text/css">
  body {{ background-color: black; color: white; }}
  pre {{ font-size: 0.8em; }}
  span.pass {{ color: green; }}
  span.alert {{ color: red; }}
  span.err {{ color: #FF7F7F; }}
  span.debug {{color: #FFFFFF; }}
  span.info {{color: #CCCCCC; }}
  span.lavainfo {{color: #B3BEE8; }}
  span.warn {{ color: #FFA500; }}
  span.timestamp {{ color: #AAFFAA; }}
  a:link {{text-decoration: none }}
  a:visited {{text-decoration: none }}
  a:active {{text-decoration: none }}
  a:hover {{text-decoration: bold; color: red; }}
  ul.results {{
    list-style-type: none;
    padding-left: 0;
    font-weight: bold;
    font-size: 1.3em;
    font-family: "Courier New", Courier, monospace;
  }}
  li.result {{ padding: 5px 0 5px 0; }}
  </style>
</head>
<body>
<h1>Boot log: {board}</h1>
"""

# datetime follows this format: 2018-12-04T10:44:15.938887
DT_RE = re.compile(r"([0-9-]+)T([0-9:.]+)")


def run(log, boot, txt, html):
    boot_result = boot.get("boot_result", "Unknown")
    if boot_result == "PASS":
        boot_result_html = "<span class=\"pass\">PASS</span>"
    elif boot_result == "FAIL":
        boot_result_html = "<span class=\"err\">FAIL</span>"
    else:
        boot_result_html = "<span class=\"warn\">{}</span>".format(boot_result)

    formats = {
        "emerg": u"<span class=\"alert\">{}</span>\n",
        "alert": u"<span class=\"alert\">{}</span>\n",
        "crit": u"<span class=\"alert\">{}</span>\n",
        "error": u"<span class=\"err\">{}</span>\n",
        "warning": u"<span class=\"warn\">{}</span>\n",
        "notice": u"<span class=\"info\">{}</span>\n",
        "info": u"<span class=\"lavainfo\">{}</span>\n",
        "debug": u"<span class=\"lavainfo\">{}</span>\n"
    }

    kernel_log_levels = {
        "0": u"<span class=\"alert\">{}</span>\n",
        "1": u"<span class=\"alert\">{}</span>\n",
        "2": u"<span class=\"alert\">{}</span>\n",
        "3": u"<span class=\"err\">{}</span>\n",
        "4": u"<span class=\"warn\">{}</span>\n",
        "5": u"<span class=\"info\">{}</span>\n",
        "6": u"<span class=\"info\">{}</span>\n",
        "7": u"<span class=\"debug\">{}</span>\n",
    }

    numbers = {
        "emerg": 0,
        "alert": 0,
        "crit": 0,
        "error": 0,
        "warning": 0,
        "notice": 0,
        "info": 0,
        "debug": 0,
    }

    kernel_numbers = {
        "0": 0,  # define KERN_EMERG
        "1": 0,  # define KERN_ALERT
        "2": 0,  # define KERN_CRIT
        "3": 0,  # define KERN_ERR
        "4": 0,  # define KERN_WARNI
        "5": 0,  # define KERN_NOTIC
        "6": 0,  # define KERN_INFO
        "7": 0   # define KERN_DEBUG
    }

    start_ts = None
    log_buffer = []

    for line in log:
        dt, level, msg = (line.get(k) for k in ["dt", "lvl", "msg"])
        raw_ts = DT_RE.match(dt).groups()[1]
        timestamp = "<span class=\"timestamp\">{}  </span>".format(raw_ts)

        if isinstance(msg, list):
            msg = ' '.join(msg)

        fmt = formats.get(level)
        if fmt:
            log_buffer.append(timestamp + fmt.format(cgi.escape(msg)))
            numbers[level] += 1
        elif level == "target":
            kernel_level = re.match(r'^\<([0-7])\>', msg)
            if kernel_level:
                fmt = kernel_log_levels[kernel_level.group(1)]
                log_buffer.append(timestamp + fmt.format(cgi.escape(msg)))
                kernel_numbers[kernel_level.group(1)] += 1
            else:
                log_buffer.append(timestamp + cgi.escape(msg) + "\n")
            txt.write(msg)
            txt.write("\n")
        elif level == "info" and msg.startswith("Start time: "):
            start_ts = msg

    html.write(HTML_HEAD.format(board=boot["board"]))
    html.write("<ul class=\"results\">")
    results = {
        "Boot result": boot_result_html,
        "Errors": numbers["error"],
        "Warnings": numbers["warning"],
        "Kernel Errors": sum(kernel_numbers[level] for level in "0123"),
        "Kernel Warnings": kernel_numbers["4"]
    }

    for title, value in results.iteritems():
        html.write("<li class=\"result\">{}: {}</li>".format(title, value))
    if start_ts:
        html.write("<li class=\"result\">{}</li>".format(start_ts))
    html.write("</ul><pre>\n")
    for line in log_buffer:
        html.write(line)
    html.write("</pre></body></html>\n")


def main(args):
    with open(args.log, "r") as log_yaml:
        log = yaml.load(log_yaml, Loader=yaml.CLoader)

    with open(args.meta, "r") as boot_json:
        boot = json.load(boot_json)

    with open(args.txt, "w") as txt, open(args.html, "w") as html:
        run(log, boot, txt, html)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Generate HTML page from kernel boot log")
    parser.add_argument("--log", required=True,
                        help="Path to a YAML file with the kernel boot log")
    parser.add_argument("--meta", required=True,
                        help="Path to a JSON file with the boot meta-data")
    parser.add_argument("--txt", required=True,
                        help="Path to the output text file")
    parser.add_argument("--html", required=True,
                        help="Path to the output HTML file")
    args = parser.parse_args()
    main(args)
