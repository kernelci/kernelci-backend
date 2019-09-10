#!/usr/bin/env python
# Copyright (C) Collabora Limited 2018
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
#
# Copyright (C) Baylibre 2017
# Author: Loys Ollivier <lollivier@baylibre.com>
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

import requests
import sys
import json
import argparse
import urllib
import urlparse


def fake_callback(backend_url, lab_name, lab_token, filename):
    headers = {
        "Authorization": lab_token
    }
    print "Looking for file {}".format(filename)
    try:
        json_file = open(filename)
    except (IOError) as err:
        print "Can't find file, error: {}".format(err)
        return
    payload = json.load(json_file)
    params = urllib.urlencode({
        'lab_name': lab_name,
        'status': 2,
        'status_string': 'complete',
    })
    url = urlparse.urljoin(backend_url, 'callback/lava/boot?{}'.format(params))
    response = requests.post(url, headers=headers, json=payload)
    print response


def parse_cmdline():
    parser = argparse.ArgumentParser(
        description="Resend a LAVA v2 callback event from a JSON file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--url', action='store',
                        help="The backend url to send callbacks to",
                        required=True)
    parser.add_argument('--lab-name', action='store',
                        help="The lab-name as registered in the backend.",
                        required=True)
    parser.add_argument('--token', action='store',
                        help="The token associated to the lab-name",
                        required=True)
    parser.add_argument('--filename', action='store',
                        help="The json file that contains the callback data.",
                        required=True)
    return parser.parse_args()


def main():
    args = parse_cmdline()
    fake_callback(args.url, args.lab_name, args.token, args.filename)


if __name__ == "__main__":
    main()
    sys.exit(0)
