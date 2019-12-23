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

"""Test module for the BisectHandler handler."""

import mock
import tornado

import urls

from handlers.tests.test_handler_base import TestHandlerBase


class TestBisectHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application([urls._BISECT_URL], **self.settings)

    def test_bisect_wrong_collection(self):
        headers = {"Authorization": "foo"}

        response = self.fetch("/bisect/bisect_id", headers=headers)
        self.assertEqual(response.code, 400)
