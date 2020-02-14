# Copyright (C) Collabora Limited 2018,2019
# Author: Michal Galka <michal.galka@collabora.com>
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
#
# Copyright (C) Baylibre 2017
# Author: Loys Ollivier <lollivier@baylibre.com>
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

"""The model that represent a test case document in the database."""

import copy
import types

import models
import models.base as mbase


# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes
class TestCaseDocument(mbase.BaseDocument):
    """Model for a test case document.

    A test case is the smallest unit of a test group: it is the actual test
    that is run and that reports a result.
    """

    def __init__(self, name, version="1.0"):
        """
        :param name: The name given to this test case.
        :type name: string
        :param version: The version of the JSON schema of this test case.
        :type version: string
        """
        self._name = name
        self._version = version

        self._created_on = None
        self._id = None
        self._index = None
        self._log_lines = []
        self._measurements = []
        self._status = None
        self._test_group_id = None

        self.arch = None
        self.build_environment = None
        self.defconfig_full = None
        self.device_type = None
        self.git_branch = None
        self.git_commit = None
        self.job = None
        self.kernel = None
        self.lab_name = None
        self.mach = None
        self.plan = None
        self.regression_id = None
        self.test_case_path = None
        self.time = -1

    @property
    def collection(self):
        return models.TEST_CASE_COLLECTION

    @property
    def name(self):
        """The name of the test case."""
        return self._name

    @property
    def version(self):
        """The schema version of this test case."""
        return self._version

    @property
    def created_on(self):
        """The creation date of this test case."""
        return self._created_on

    @created_on.setter
    def created_on(self, value):
        """Set the creation date of this test case."""
        if self._created_on:
            raise AttributeError("created_on already set")
        self._created_on = value

    @property
    def id(self):
        """The id of the test case as registered in the database."""
        return self._id

    @id.setter
    def id(self, value):
        """Set the test case id."""
        if self._id:
            raise AttributeError("id already set")
        self._id = value

    @property
    def index(self):
        """The index of the test case to keep its order within a group."""
        return self._index

    @index.setter
    def index(self, value):
        """Set the test case index."""
        if self._index:
            raise AttributeError("index already set")
        self._index = value

    @property
    def log_lines(self):
        """The log lines stored for the test case."""
        return self._log_lines

    @log_lines.setter
    def log_lines(self, value):
        """Set the log lines associated with the test case.

        :param value: The list of log lines to store.
        :type value: list
        """
        if not value:
            value = []
        if not isinstance(value, types.ListType):
            raise ValueError("Log lines must be passed as a list")
        self._log_lines = value

    def add_log_lines(self, log_line):
        """Add a single log line to the test case.

        A log_line should be a non-empty dictionary-like data structure.
        Empty values will not be stored in this data structure. Typically it'll
        have a 'dt' and 'msg' keys which are respectively the timestamp
        and the message.

        :param log_line: A log_line to store
        :type log_line: dict
        """
        if all([log_line, isinstance(log_line, types.DictionaryType)]):
            self._log_lines.append(log_line)
        else:
            raise ValueError(
                "Log line must be non-empty dictionary-like object")

    @property
    def measurements(self):
        """The measurements registered by this test case."""
        return self._measurements

    @measurements.setter
    def measurements(self, value):
        """Set the measurements registered by this test case.

        :param value: The registered measurements.
        :type value: list
        """
        if not value:
            value = []
        if not isinstance(value, types.ListType):
            raise ValueError("Measurements must be passed as a list")
        self._measurements = value

    def add_measurement(self, measurement):
        """Add a single measurement to this test case.

        A measurement should be a non-empty dictionary-like data structure.
        Empty values will not be stored in this data structure. To register an
        empty result it is still necessary to provide a valid measurement data
        structure.

        :param measurement: The registered measurement.
        :type measurement: dict
        """
        if all([measurement, isinstance(measurement, types.DictionaryType)]):
            self._measurements.append(measurement)
        else:
            raise ValueError(
                "Measurement must be non-empty dictionary-like object")

    @property
    def status(self):
        """The status of this test case."""
        return self._status

    @status.setter
    def status(self, value):
        """Set the status of this test case.

        :param value: The status name.
        :type value: string
        """
        if all([value, value in models.VALID_TEST_CASE_STATUS]):
            self._status = value
        else:
            raise ValueError("Unsupported status value provided")

    @property
    def test_group_id(self):
        """The ID of the associated test group."""
        return self._test_group_id

    @test_group_id.setter
    def test_group_id(self, value):
        """Set the associated test group ID.

        :param value: The test group ID.
        :type value: string
        """
        if self._test_group_id:
            raise AttributeError("group_id already set")
        self._test_group_id = value

    def to_dict(self):
        test_case = {
            models.ARCHITECTURE_KEY: self.arch,
            models.BUILD_ENVIRONMENT_KEY: self.build_environment,
            models.CREATED_KEY: self.created_on,
            models.DEFCONFIG_FULL_KEY: self.defconfig_full,
            models.DEVICE_TYPE_KEY: self.device_type,
            models.GIT_BRANCH_KEY: self.git_branch,
            models.GIT_COMMIT_KEY: self.git_commit,
            models.INDEX_KEY: self.index,
            models.JOB_KEY: self.job,
            models.KERNEL_KEY: self.kernel,
            models.LAB_NAME_KEY: self.lab_name,
            models.LOG_LINES_KEY: self.log_lines,
            models.MACH_KEY: self.mach,
            models.MEASUREMENTS_KEY: self.measurements,
            models.NAME_KEY: self.name,
            models.PLAN_KEY: self.plan,
            models.REGRESSION_ID_KEY: self.regression_id,
            models.STATUS_KEY: self.status,
            models.TEST_CASE_PATH_KEY: self.test_case_path,
            models.TEST_GROUP_ID_KEY: self.test_group_id,
            models.TIME_KEY: self.time,
            models.VERSION_KEY: self.version,
        }

        if self.id:
            test_case[models.ID_KEY] = self.id

        return test_case

    @staticmethod
    def from_json(json_obj):
        test_case = None
        if isinstance(json_obj, types.DictionaryType):
            local_obj = copy.deepcopy(json_obj)
            doc_pop = local_obj.pop

            set_id = doc_pop(models.ID_KEY, None)

            try:
                name = doc_pop(models.NAME_KEY)
                version = doc_pop(models.VERSION_KEY)

                test_case = TestCaseDocument(name, version)
                test_case.id = set_id

                for key, val in local_obj.iteritems():
                    setattr(test_case, key, val)
            except KeyError:
                # Missing mandatory key? Return None.
                test_case = None

        return test_case
