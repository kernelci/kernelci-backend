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
import celery.schedules
import celery.signals
from celery.bin import Option
import io
import kombu.serialization
import os
import utils
from utils.kcidb import KcidbSubmit

import taskqueue.celeryconfig as celeryconfig
import taskqueue.serializer as serializer


DEFAULT_CELERY_CONFIG_FILE = "/etc/kernelci/kernelci-celery.cfg"
TASKS_LIST = [
    "taskqueue.tasks.bisect",
    "taskqueue.tasks.build",
    "taskqueue.tasks.callback",
    "taskqueue.tasks.common",
    "taskqueue.tasks.kcidb",
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

app.user_options['preload'].add(
    Option('-u', '--user-config', default=DEFAULT_CELERY_CONFIG_FILE,
           help='User configuration file to use'),
)
app.config_from_object(celeryconfig)

# Periodic tasks to be executed.
CELERYBEAT_SCHEDULE = {
    "calculate-daily-stats": {
        "task": "calculate-daily-statistics",
        "schedule": celery.schedules.crontab(minute=1, hour=12)
    }
}


@celery.signals.user_preload_options.connect
def on_preload_parsed(options, **kwargs):
    # Read from a config file from disk.
    user_config = options['user_config']
    if os.path.isfile(user_config):
        with io.open(user_config) as conf:
            updates = ast.literal_eval(conf.read())
        app.conf.update(updates)
    else:
        utils.LOG.warn('Celery configuration file not found: {}'
                       .format(user_config))


app.conf.update(CELERYBEAT_SCHEDULE=CELERYBEAT_SCHEDULE)

app.kcidb_pool = {}


@celery.signals.worker_process_init.connect
def worker_init_handler(*args, **kwargs):
    kcidb_options = app.conf.get("kcidb_options")
    if kcidb_options:
        pid = os.getpid()
        if kcidb_options.get("debug"):
            utils.LOG.info("Creating KcidbSubmit object for PID: {}"
                           .format(pid))
        app.kcidb_pool[pid] = KcidbSubmit(kcidb_options)


@celery.signals.worker_process_shutdown.connect
def worker_process_init_handler(*args, **kwargs):
    kcidb_options = app.conf.get("kcidb_options")
    if kcidb_options:
        pid = os.getpid()
        kcidb_submit = app.kcidb_pool.get(pid)
        if kcidb_submit:
            if kcidb_options.get("debug"):
                utils.LOG.info('Terminating kcidb-submit for worker pid: {}'
                               .format(pid))
            kcidb_submit.terminate()
        elif kcidb_options.get("debug"):
            utils.LOG.info('No kcidb-submit for worker pid: {}'.format(pid))


if __name__ == "__main__":
    app.start()
