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

import handlers.base as hbase
import handlers.response as hresponse
import models
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

        taskq.import_build.apply_async(
            [kwargs["json_obj"]],
            link=[taskq.parse_single_build_log.s()]
        )

        return response

    def _delete(self, defconf_id, **kwargs):
        response = hresponse.HandlerResponse()
        response.status_code = utils.db.delete(self.collection, defconf_id)

        if response.status_code == 200:
            response.reason = "Resource '%s' deleted" % defconf_id

        return response
