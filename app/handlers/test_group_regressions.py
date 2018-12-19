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

"""The RequestHandler for /test[/<id>]/regressions/ URLs."""

import bson

import handlers.base as hbase
import handlers.response as hresponse
import models
import utils.db

from utils.kci_test.regressions import (
    create_regressions_key,
    get_regressions_by_key
)

# TODO: code for handling /test[/<id>]/regressions/ URLs.
#  class TestGroupRegressionsHandler(hbase.BaseHandler):
#        """Handle test group regressions request."""


def find_regressions(doc_id, database):
    """Look for the regressions of a test group report.

    :param doc_id: The id of the test group to look for regressions.
    :type doc_id: ObjectId
    :return HandlerResponse A HandlerResponse object.
    """
    response = hresponse.HandlerResponse()
    # First make sure we have a valid test_group_id value.
    test_group_doc = utils.db.find_one2(
        database[models.TEST_GROUP_COLLECTION], doc_id)

    if test_group_doc:
        regr_idx_doc = utils.db.find_one2(
            database[models.TEST_GROUP_REGRESSIONS_BY_TEST_GROUP_COLLECTION],
            {models.TEST_GROUP_ID_KEY: doc_id})

        if regr_idx_doc:
            spec = {
                models.ID_KEY:
                    regr_idx_doc[models.TEST_GROUP_REGRESSIONS_ID_KEY]
            }

            result = utils.db.find_one2(
                database[models.TEST_GROUP_REGRESSIONS_COLLECTION],
                spec, fields=[models.REGRESSIONS_KEY])

            if result:
                response.result = get_regressions_by_key(
                    create_regressions_key(test_group_doc),
                    result[models.REGRESSIONS_KEY])
                response.count = len(response.result)
    else:
        response.status_code = 404
        response.reason = "Resource '{:s}' not found".format(str(doc_id))

    return response
