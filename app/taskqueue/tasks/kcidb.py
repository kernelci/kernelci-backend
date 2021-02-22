# Copyright (C) Collabora Limited 2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
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

"""All kcidb related tasks."""

import os
import taskqueue.celery as taskc
import utils
import utils.kcidb


@taskc.app.task(name="kcidb-build")
def push_build(args):
    build_id, job_id, first = args
    kcidb_options = taskc.app.conf.get("kcidb_options")
    pid = os.getpid()
    kcidb_submit = taskc.app.kcidb_pool.get(pid)
    if kcidb_options:
        try:
            utils.kcidb.push_build(build_id, first, kcidb_options,
                                   kcidb_submit.process,
                                   taskc.app.conf.db_options)
        except Exception, e:
            utils.LOG.exception(e)

    return build_id, job_id


@taskc.app.task(name="kcidb-tests")
def push_tests(group_id):
    kcidb_options = taskc.app.conf.get("kcidb_options")
    pid = os.getpid()
    kcidb_submit = taskc.app.kcidb_pool[pid]
    if kcidb_options:
        try:
            utils.kcidb.push_tests(group_id, kcidb_options,
                                   kcidb_submit,
                                   taskc.app.conf.db_options)
        except Exception, e:
            utils.LOG.exception(e)

    return group_id
