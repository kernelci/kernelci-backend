# Copyright (C) Linaro Limited 2014
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

"""Provide a simple /version handler."""

import handlers
import handlers.base as hbase
import handlers.response as hresponse
import models


# pylint: disable=too-many-public-methods
class VersionHandler(hbase.BaseHandler):
    """Handle request to the /version URL.

    Provide the backend version number in use.
    """

    def __init__(self, application, request, **kwargs):
        super(VersionHandler, self).__init__(application, request, **kwargs)

    def execute_get(self, *args, **kwargs):
        response = hresponse.HandlerResponse()
        response.result = [
            {
                models.VERSION_FULL_KEY: handlers.__versionfull__,
                models.VERSION_KEY: handlers.__version__,
            }
        ]
        return response

    def execute_post(self, *args, **kwargs):
        return hresponse.HandlerResponse(501)

    def execute_delete(self, *args, **kwargs):
        return hresponse.HandlerResponse(501)
