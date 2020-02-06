# Copyright (C) Collabora Limited 2020
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

"""The RequestHandler for /test/regression URLs."""

import handlers.test_base
import models


# pylint: disable=too-many-public-methods
class TestRegressionHandler(handlers.test_base.TestBaseHandler):
    """The test regression request handler."""

    def __init__(self, application, request, **kwargs):
        super(TestRegressionHandler, self).__init__(
            application, request, **kwargs)

    @property
    def collection(self):
        return self.db[models.TEST_REGRESSION_COLLECTION]

    @staticmethod
    def _valid_keys(method):
        return models.TEST_REGRESSION_VALID_KEYS.get(method)
