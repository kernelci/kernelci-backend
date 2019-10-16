# Copyright (C) Collabora Limited 2017
# Author: Guillaume Tucker <guillaume@mangoz.org>
#
# Copyright (C) Linaro Limited -0700,2014,2015,2016
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

"""The Celery application."""

from __future__ import absolute_import

import ast
import celery
import celery.schedules
import io
import kombu.serialization
import os

import taskqueue.celeryconfig as celeryconfig
import taskqueue.serializer as serializer


CELERY_CONFIG_FILE = "/etc/kernelci/kernelci-celery.cfg"
TASKS_LIST = [
    "taskqueue.tasks.bisect",
    "taskqueue.tasks.boot",
    "taskqueue.tasks.build",
    "taskqueue.tasks.callback",
    "taskqueue.tasks.common",
    "taskqueue.tasks.compare",
    "taskqueue.tasks.report",
    "taskqueue.tasks.stats",
    "taskqueue.tasks.test"
]

# Register the custom decoder/encoder for celery with the name "kjson".
# This is in all effect a JSON format, with some extensions.
kombu.serialization.register(
    "kjson",
    serializer.kernelci_json_encoder,
    serializer.kernelci_json_decoder,
    content_type="application/json",
    content_encoding="utf-8"
)

app = celery.Celery(
    "tasks",
    include=TASKS_LIST
)

app.config_from_object(celeryconfig)

# Periodic tasks to be executed.
CELERYBEAT_SCHEDULE = {
    "calculate-daily-stats": {
        "task": "calculate-daily-statistics",
        "schedule": celery.schedules.crontab(minute=1, hour=12)
    }
}

# Read from a config file from disk.
if os.path.exists(CELERY_CONFIG_FILE):
    with io.open(CELERY_CONFIG_FILE) as conf_file:
        updates = ast.literal_eval(conf_file.read())

    app.conf.update(updates)

app.conf.update(CELERYBEAT_SCHEDULE=CELERYBEAT_SCHEDULE)


if __name__ == "__main__":
    app.start()
