# Copyright (C) Linaro Limited 2015,2017
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

"""The RequestHandler for /build URLs."""

import celery
import handlers.base as hbase
import handlers.response as hresponse
import models
import taskqueue.tasks
import taskqueue.tasks.kcidb
import taskqueue.tasks.build as taskq
import utils.db


class BuildHandler(hbase.BaseHandler):
    """Handle the /build URLs."""

    def __init__(self, application, request, **kwargs):
        super(BuildHandler, self).__init__(application, request, **kwargs)

    @property
    def collection(self):
        return self.db[models.BUILD_COLLECTION]

    @staticmethod
    def _valid_keys(method):
        return models.BUILD_VALID_KEYS.get(method, None)

    def _post(self, *args, **kwargs):
        response = hresponse.HandlerResponse(202)
        response.reason = "Request accepted and being imported"

        tasks = [
            taskq.import_build.s(kwargs["json_obj"]),
            taskqueue.tasks.kcidb.push_build.s(),
            taskq.parse_single_build_log.s(),
        ]
        celery.chain(tasks).apply_async(
            link_error=taskqueue.tasks.error_handler.s())

        return response
