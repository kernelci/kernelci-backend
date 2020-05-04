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

"""The /batch RequestHandler to perform batch operations."""

try:
    import simplejson as json
except ImportError:
    import json

import handlers.base as hbase
import handlers.common.request
import handlers.response as hresponse
import models
import taskqueue.tasks.common as taskq
import utils.validator as validator


class BatchHandler(hbase.BaseHandler):
    """The batch URL handler class."""

    def __init__(self, application, request, **kwargs):
        super(BatchHandler, self).__init__(application, request, **kwargs)
        self._operations = []

    @staticmethod
    def _valid_keys(method):
        return models.BATCH_VALID_KEYS.get(method, None)

    def execute_get(self):
        return hresponse.HandlerResponse(501)

    def execute_delete(self):
        return hresponse.HandlerResponse(501)

    def execute_post(self):
        response = None
        valid_token, _ = self.validate_req_token("POST")

        if valid_token:
            valid_request = handlers.common.request.valid_post_request(
                self.request.headers, self.request.remote_ip)

            if valid_request == 200:
                try:
                    json_obj = json.loads(self.request.body.decode("utf8"))

                    if validator.is_valid_batch_json(
                            json_obj,
                            models.BATCH_KEY,
                            self._valid_keys("POST")):
                        response = hresponse.HandlerResponse(200)
                        response.result = \
                            self.prepare_and_perform_batch_ops(
                                json_obj, self.settings["dboptions"]
                            )
                    else:
                        response = hresponse.HandlerResponse(400)
                        response.reason = "Provided JSON is not valid"
                except ValueError:
                    error = "No JSON data found in the POST request"
                    self.log.error(error)
                    response = hresponse.HandlerResponse(422)
                    response.reason = error
            else:
                response = hresponse.HandlerResponse(valid_request)
                response.reason = self._get_status_message(valid_request)
        else:
            response = hresponse.HandlerResponse(403)

        return response

    @staticmethod
    def prepare_and_perform_batch_ops(json_obj, db_options):
        """Perform the operation defined in the JSON object.

        The JSON oject must be a valid batch operations object.

        :param json_obj: The JSON object that defines all the bath operations
        to perform.
        :type json_obj: dict
        :param db_options: The mongodb database connection parameters.
        :type db_options: dict
        """
        return taskq.execute_batch_serial(
            json_obj.get(models.BATCH_KEY), db_options
        )
