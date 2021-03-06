# Copyright (C) Collabora Limited 2018,2019
# Author: Michal Galka <michal.galka@collabora.com>
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
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

import unittest
from datetime import datetime

import models.base as mbase
import models.test_case as mtcase


class TestTestCaseModel(unittest.TestCase):

    def test_case_doc_valid_instance(self):
        test_case = mtcase.TestCaseDocument("name")
        self.assertIsInstance(test_case, mbase.BaseDocument)
        self.assertEqual(test_case.collection, "test_case")

    def test_case_doc_to_dict(self):
        test_case = mtcase.TestCaseDocument("name", "1.1")

        test_case.id = "id"
        test_case.arch = "gothic"
        test_case.created_on = "now"
        test_case.build_environment = "tcc-0.9"
        test_case.defconfig_full = "defconfig+SOMETHING=y"
        test_case.device_type = "supercar"
        test_case.git_branch = "branch"
        test_case.git_commit = "1234abc"
        test_case.index = 1
        test_case.job = "this-job"
        test_case.kernel = "v123.45"
        test_case.lab_name = "secret"
        test_case.log_lines = [{
            'dt': datetime(1970, 1, 1, 0, 0, 0),
            'msg': 'foo'}]
        test_case.device_type = "supercar"
        test_case.mach = "batmobile"
        test_case.measurements = [{"foo": 1}]
        test_case.plan = "cunning"
        test_case.regression_id = 1234
        test_case.status = "FAIL"
        test_case.test_case_path = "test.case.path"
        test_case.test_group_id = "another_id"
        test_case.time = 10

        expected = {
            "_id": "id",
            "arch": "gothic",
            "build_environment": "tcc-0.9",
            "created_on": "now",
            "defconfig_full": "defconfig+SOMETHING=y",
            "device_type": "supercar",
            "git_branch": "branch",
            "git_commit": "1234abc",
            "index": 1,
            "job": "this-job",
            "kernel": "v123.45",
            "lab_name": "secret",
            "log_lines": [{
               'dt': datetime(1970, 1, 1, 0, 0, 0),
               'msg': 'foo'}],
            "mach": "batmobile",
            "measurements": [{"foo": 1}],
            "name": "name",
            "plan": "cunning",
            "regression_id": 1234,
            "status": "FAIL",
            "test_case_path": "test.case.path",
            "test_group_id": "another_id",
            "time": 10,
            "version": "1.1"
        }

        self.assertDictEqual(expected, test_case.to_dict())

    def test_case_doc_to_dict_no_id(self):
        test_case = mtcase.TestCaseDocument("name", "1.1")

        test_case.arch = "gothic"
        test_case.build_environment = "tcc-0.9"
        test_case.created_on = "now"
        test_case.defconfig_full = "defconfig+SOMETHING=y"
        test_case.device_type = "pi"
        test_case.git_branch = "branch"
        test_case.git_commit = "1234abc"
        test_case.index = 1
        test_case.job = "this-job"
        test_case.kernel = "v123.45"
        test_case.lab_name = "area51"
        test_case.log_lines = [{
            'dt': datetime(1970, 1, 1, 0, 0, 0),
            'msg': 'foo'}]
        test_case.mach = "raspberry"
        test_case.measurements = [{"foo": 1}]
        test_case.plan = "cunning"
        test_case.regression_id = 1234
        test_case.status = "FAIL"
        test_case.test_case_path = "test.case.path"
        test_case.test_group_id = "another_id"
        test_case.time = 10

        expected = {
            "arch": "gothic",
            "build_environment": "tcc-0.9",
            "created_on": "now",
            "defconfig_full": "defconfig+SOMETHING=y",
            "device_type": "pi",
            "git_branch": "branch",
            "git_commit": "1234abc",
            "index": 1,
            "job": "this-job",
            "kernel": "v123.45",
            "lab_name": "area51",
            "log_lines": [{
                'dt': datetime(1970, 1, 1, 0, 0, 0),
                'msg': 'foo'}],
            "device_type": "pi",
            "mach": "raspberry",
            "measurements": [{"foo": 1}],
            "name": "name",
            "plan": "cunning",
            "regression_id": 1234,
            "status": "FAIL",
            "test_case_path": "test.case.path",
            "test_group_id": "another_id",
            "time": 10,
            "version": "1.1"
        }

        self.assertDictEqual(expected, test_case.to_dict())

    def test_case_doc_from_json_missing_key(self):
        test_case = {
            "_id": "id"
        }

        self.assertIsNone(mtcase.TestCaseDocument.from_json(test_case))

    def test_case_doc_from_json_wrong_type(self):
        self.assertIsNone(mtcase.TestCaseDocument.from_json([]))
        self.assertIsNone(mtcase.TestCaseDocument.from_json(()))
        self.assertIsNone(mtcase.TestCaseDocument.from_json(""))

    def test_case_doc_from_json(self):
        case_json = {
            "_id": "id",
            "arch": "gothic",
            "build_environment": "tcc-0.9",
            "created_on": "now",
            "defconfig_full": "defconfig+SOMETHING=y",
            "device_type": "pi",
            "git_branch": "branch",
            "git_commit": "1234abc",
            "index": 1,
            "job": "this-job",
            "kernel": "v123.45",
            "lab_name": "spaghetti",
            "log_lines": [{
                'dt': datetime(1970, 1, 1, 0, 0, 0),
                'msg': 'foo'}],
            "mach": "laptop",
            "measurements": [{"foo": 1}],
            "name": "name",
            "plan": "cunning",
            "regression_id": 1234,
            "status": "FAIL",
            "test_case_path": "test.case.path",
            "test_group_id": "another_id",
            "time": 10,
            "version": "1.1"
        }

        test_case = mtcase.TestCaseDocument.from_json(case_json)

        self.assertIsInstance(test_case, mtcase.TestCaseDocument)
        self.assertDictEqual(case_json, test_case.to_dict())

    def test_case_doc_measurements_setter(self):
        test_case = mtcase.TestCaseDocument("name")

        def measurements_setter(value):
            test_case.measurements = value

        self.assertRaises(ValueError, measurements_setter, {"foo": "bar"})
        self.assertRaises(ValueError, measurements_setter, "foo")

        measurements_setter([])
        self.assertListEqual([], test_case.measurements)
        measurements_setter(())
        self.assertListEqual([], test_case.measurements)
        measurements_setter(None)
        self.assertListEqual([], test_case.measurements)
        measurements_setter("")
        self.assertListEqual([], test_case.measurements)
        measurements_setter({})
        self.assertListEqual([], test_case.measurements)

    def test_case_doc_add_measurement(self):
        test_case = mtcase.TestCaseDocument("name")

        def add_measurement(value):
            test_case.add_measurement(value)

        test_case.measurements = [{"foo": "bar"}]
        test_case.add_measurement({"baz": "foo"})

        expected = [{"foo": "bar"}, {"baz": "foo"}]
        self.assertListEqual(expected, test_case.measurements)

        self.assertRaises(ValueError, add_measurement, "")
        self.assertRaises(ValueError, add_measurement, [])
        self.assertRaises(ValueError, add_measurement, {})
        self.assertRaises(ValueError, add_measurement, ())

    def test_case_doc_set_status(self):
        test_case = mtcase.TestCaseDocument("name")

        def set_status(value):
            test_case.status = value

        set_status("PASS")
        self.assertEqual("PASS", test_case.status)
        self.assertRaises(ValueError, set_status, "FOO")
        self.assertRaises(ValueError, set_status, "")
        self.assertRaises(ValueError, set_status, 1)
        self.assertRaises(ValueError, set_status, {})
        self.assertRaises(ValueError, set_status, [])
        self.assertRaises(ValueError, set_status, ())

    def test_name(self):
        test_case = mtcase.TestCaseDocument("foo")
        self.assertEqual("foo", test_case.name)
