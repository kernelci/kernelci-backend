# Copyright (C) Collabora Limited 2017, 2018, 2019, 2020
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
# Author: Michal Galka <michal.galka@collabora.com>
#
# Copyright (C) Linaro Limited 2015,2016
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

"""The RequestHandler for /test/case URLs."""

import handlers.test_base as htbase
import models


# pylint: disable=too-many-public-methods
class TestCaseHandler(htbase.TestBaseHandler):
    """The test set request handler."""

    def __init__(self, application, request, **kwargs):
        super(TestCaseHandler, self).__init__(application, request, **kwargs)

    @property
    def collection(self):
        return self.db[models.TEST_CASE_COLLECTION]

    @staticmethod
    def _valid_keys(method):
        return models.TEST_CASE_VALID_KEYS.get(method, None)
