# Copyright (C) Linaro Limited 2014,2016
# Author: Milo Casagrande <milo.casagrande@linaro.org>
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

"""Logging facilities."""

import logging

LOG = None


def get_log(debug=False):
    """Retrieve a logger.

    :param debug: If debug level should be turned on.
    :return: A logger instance.
    """
    global LOG

    if LOG is None:
        LOG = logging.getLogger()
        log_handler = logging.StreamHandler()

        formatter = logging.Formatter(
            '[%(levelname)8s/%(threadName)10s] %(message)s')
        log_handler.setFormatter(formatter)

        if debug:
            log_handler.setLevel(logging.DEBUG)
            LOG.setLevel(logging.DEBUG)
        else:
            log_handler.setLevel(logging.INFO)
            LOG.setLevel(logging.INFO)

        LOG.addHandler(log_handler)

    return LOG
