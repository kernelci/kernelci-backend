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

import taskqueue.celery as taskc
import utils
import utils.kcidb


@taskc.app.task(name="kcidb-build")
def push_build(args):
    build_id, job_id, first = args
    bq_options = taskc.app.conf.get("BigQuery_options")
    if bq_options:
        utils.kcidb.push_build(build_id, first, bq_options,
                               taskc.app.conf.db_options)
    return build_id, job_id
