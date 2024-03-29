# Copyright (C) Collabora Limited 2017
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
#
# Copyright (C) Linaro Limited 2015
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

"""Functions and classes to handle errors data structure."""

import utils

LOG = utils.log.get_log()


class BackendError(Exception):

    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return ", ".join([" ".join([str(k)] + v)
                          for k, v in self.errors.iteritems()])


def update_errors(to_update, errors):
    """Update the errors dictionary from another one.

    :param to_update: The dictionary to be updated.
    :type to_update: dictionary
    :param errors: The dictionary whose elements will be added.
    :type errors: dictionary
    """
    if errors:
        to_update_keys = to_update.viewkeys()
        for k, v in errors.iteritems():
            if k in to_update_keys:
                to_update[k].extend(v)
            else:
                to_update[k] = v


def add_error(errors, err_code, err_msg):
    """Add error code and message to the provided dictionary.

    :param errors: The dictionary that will store the error codes and messages.
    :type errors: dictionary
    :param err_code: The error code that will be used as a key.
    :type err_code: int
    :param err_msg: The message to store.
    :type err_msg: string
    """
    if all([err_code, err_msg]):
        if err_code in errors.viewkeys():
            errors[err_code].append(err_msg)
        else:
            errors[err_code] = []
            errors[err_code].append(err_msg)


def handle_errors(ex=None, msg=None, errors=None):
    """Handles data processing errors

    Handles data processing errors by logging issues
    and/or raising exceptions appropriate exceptions.

    :param ex: exception to log
    :type ex: Exception
    :param msg: Message to log
    :type msg: str
    :param errors: errors to raise as BackendError
    :type errors: dict
    """
    if ex is not None:
        LOG.exception(ex)
    if msg is not None:
        LOG.error(msg)
    if errors:
        raise BackendError(errors)
