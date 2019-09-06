# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The RequestHandler for /test/case URLs."""

import bson

import handlers.response as hresponse
import handlers.test_base as htbase
import models
import utils.db
import utils.tests_import as tests_import


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
