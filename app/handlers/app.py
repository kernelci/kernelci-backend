# Copyright (C) Linaro Limited 2014,2015
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

"""
A very simple RequestHandler used as the default one for the Tornado
application.
"""

import tornado.web


class AppHandler(tornado.web.RequestHandler):
    """This handler is used to provide custom error messages.

    It is used to provide JSON response on errors, and the only implemented
    method is `write_error'.
    """

    def __init__(self, application, request, **kwargs):
        super(AppHandler, self).__init__(application, request, **kwargs)

    def write_error(self, status_code, **kwargs):
        self.set_status(404, "Resource not found")
        self.write(dict(code=404, message="Resource not found"))
        self.finish()
