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

import celery.result
import taskqueue.celery as taskc
import utils


@taskc.app.task(name="error-handler")
def error_handler(uuid):
    # ToDo: propagate error if the HTTP response hasn't been sent already
    with celery.result.allow_join_result():
        result = celery.result.AsyncResult(uuid)
        ex = result.get(propagate=False)
        utils.LOG.error("Task failed, UUID: {}, error: {}".format(uuid, ex))
