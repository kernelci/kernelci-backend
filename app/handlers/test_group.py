# Copyright (C) Collabora Limited 2018,2019
# Author: Michal Galka <michal.galka@collabora.com>
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

"""The RequestHandler for /test/group URLs."""

import bson
import datetime
import os
import types

import handlers.response as hresponse
import handlers.test_base as htbase
import models
import models.test_group as mtgroup
import taskqueue.tasks.test as taskq
import utils
import utils.db
from utils import kci_test


# pylint: disable=too-many-public-methods
# pylint: disable=invalid-name
class TestGroupHandler(htbase.TestBaseHandler):
    """The test group request handler."""

    def __init__(self, application, request, **kwargs):
        super(TestGroupHandler, self).__init__(application, request, **kwargs)

    @property
    def collection(self):
        return self.db[models.TEST_GROUP_COLLECTION]

    @staticmethod
    def _valid_keys(method):
        return models.TEST_GROUP_VALID_KEYS.get(method, None)

    def _post(self, *args, **kwargs):
        response = hresponse.HandlerResponse()
        group_id = kwargs.get("id", None)

        if group_id:
            response.status_code = 400
            response.reason = "To update a test group, use a PUT request"
        else:
            # TODO: double check the token with its lab name, we need to make
            # sure people are sending test reports with a token lab with the
            # correct lab name value.
            group_json = kwargs.get("json_obj", None)
            group_pop = group_json.pop
            group_get = group_json.get

            group_name = group_get(models.NAME_KEY)
            # TODO: move name validation into the initial json validation.
            if utils.valid_test_name(group_name):
                if group_get(models.LOG_KEY):
                    path_parts = (utils.BASE_PATH,
                                  group_get(models.JOB_KEY),
                                  group_get(models.GIT_BRANCH_KEY),
                                  group_get(models.KERNEL_KEY),
                                  group_get(models.ARCHITECTURE_KEY),
                                  group_get(models.DEFCONFIG_FULL_KEY),
                                  group_get(models.BUILD_ENVIRONMENT_KEY),
                                  group_get(models.LAB_NAME_KEY))
                    directory_path = os.path.join(*path_parts)

                    name = "-".join((group_get(models.NAME_KEY),
                                     group_get(models.BOARD_KEY)))
                    ext = 'txt'
                    filename = "{}.{}".format(name, ext)
                    kci_test._add_test_log(directory_path,
                                           filename,
                                           group_get(models.LOG_KEY))
                    group_json[models.BOOT_LOG_KEY] = filename

                dboptions = self.settings["dboptions"]
                (ret_val,
                 group_id,
                 errors) = kci_test.import_and_save_kci_tests(group_json,
                                                              dboptions)

                if ret_val == 201:
                    response.status_code = ret_val
                    response.result = {models.ID_KEY: group_id}
                    response.reason = (
                        "Test group '%s' created" %
                        group_name)
                    response.headers = {
                        "Location": "/test/group/%s" % str(group_id)}
                else:
                    response.status_code = ret_val
                    response.reason = (
                        "Error saving test group '%s'" % group_name)
            else:
                response.status_code = 400
                response.reason = "Test group name not valid"

        return response
