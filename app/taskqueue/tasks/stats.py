# Copyright (C) Linaro Limited 2015,2016,2017
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

"""Tasks to calculate statistics."""

import taskqueue.celery as taskc

import utils
import utils.db
import utils.stats.daily


@taskc.app.task(name="calculate-daily-statistics")
def calculate_daily_statistics():
    """Collect daily statistics on the data stored."""
    db_options = taskc.app.conf.db_options
    daily_stats = utils.stats.daily.calculate_daily_stats(db_options)

    database = utils.db.get_db_connection(db_options)
    ret_val, doc_id = utils.db.save(database, daily_stats, manipulate=True)

    return ret_val, doc_id
