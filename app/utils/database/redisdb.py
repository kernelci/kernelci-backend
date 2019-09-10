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

"""Perform basic Redis operations."""

import redis


REDIS_CONNECTION = None


def get_db_connection(db_options, db_num=0):
    """Get a Redis DB Connection.

    :param db_options: The database connection options.
    :type db_options: dict
    :return A Redis connection.
    """
    global REDIS_CONNECTION

    if not REDIS_CONNECTION:
        db_options_get = db_options.get

        redis_host = db_options_get("redis_host", "localhost")
        redis_port = db_options_get("redis_port", 6379)
        redis_pwd = db_options_get("redis_password", "")
        redis_db = db_options_get("redis_db", db_num)

        if redis_pwd:
            REDIS_CONNECTION = redis.StrictRedis(
                host=redis_host,
                port=redis_port, db=redis_db, password=redis_pwd)
        else:
            REDIS_CONNECTION = redis.StrictRedis(
                host=redis_host, port=redis_port, db=redis_db)

    return REDIS_CONNECTION
