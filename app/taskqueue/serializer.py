# Copyright (C) Linaro Limited 2015,2016
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

"""Custom kernel-ci JSON serializer/deserializer to be used with Celery.

The following module defines two custom functions to serialize and deserialize
JSON objects that use BSON notation. These functions are intended to be used
as the defual encoder/decoder functions that Celery uses to send messages.
"""

try:
    import simplejson as json
except ImportError:
    import json

from bson.json_util import (
    default,
    object_hook
)


def kernelci_json_encoder(obj):
    """Custom JSON serialization function.

    :param obj: The object to serialize.
    :type obj: dict
    :return A unicode string.
    """
    return json.dumps(
        obj, default=default, ensure_ascii=False, separators=(",", ":"))


def kernelci_json_decoder(obj):
    """Custome JSON deserialization function.

    :param obj: The object to deserialize.
    :type obj: string or unicode
    :return A JSON object.
    """
    return json.loads(obj, object_hook=object_hook)
