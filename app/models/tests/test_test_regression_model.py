# Copyright (C) Collabora Limited 2019
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

import unittest

import models
import models.base as mbase
import models.test_regression as mtregr


class TestTestRegressionModel(unittest.TestCase):

    def test_regression_doc_valid_instance(self):
        test_regr = mtregr.TestRegressionDocument(
            "job", "kernel", "git_branch", "git_url", "defconfig_full", "benv",
            "device_type", "arch", ["hierarchy"], "plan", "hierarchy")
        self.assertIsInstance(test_regr, mbase.BaseDocument)

    def test_regression_doc_to_dict(self):
        test_regr = mtregr.TestRegressionDocument(
            "steady", "kernel-123", "a-branch", "a-url", "defconfig_full+abc",
            "concrete", "imaginary-device", "farm", ["hier", "ar", "chy"],
            "hier", "hier.ar.chy")

        test_regr.id = "id"
        test_regr.version = "version"
        test_regr._created_on = "then"

        test_regr.add_regression({
            models.TEST_CASE_ID_KEY: "test-case-id",
            models.CREATED_KEY: "never",
            models.STATUS_KEY: "PASS",
            models.KERNEL_KEY: "kernel-001",
            models.GIT_COMMIT_KEY: "1234abcd",
            models.LAB_NAME_KEY: "secret-lab",
            models.BUILD_ID_KEY: "build-id",
            models.PLAN_VARIANT_KEY: "cunning",
        })

        expected = {
            "_id": "id",
            "created_on": "then",
            "version": "version",
            "job": "steady",
            "kernel": "kernel-123",
            "git_branch": "a-branch",
            "git_url": "a-url",
            "defconfig_full": "defconfig_full+abc",
            "build_environment": "concrete",
            "device_type": "imaginary-device",
            "arch": "farm",
            "hierarchy": ["hier", "ar", "chy"],
            "plan": "hier",
            "test_case_path": "hier.ar.chy",
            "compiler": None,
            "compiler_version": None,
            "regressions": [
                {
                    "test_case_id": "test-case-id",
                    "created_on": "never",
                    "status": "PASS",
                    "kernel": "kernel-001",
                    "git_commit": "1234abcd",
                    "lab_name": "secret-lab",
                    "build_id": "build-id",
                    "plan_variant": "cunning",
                },
            ],
        }

        self.assertDictEqual(expected, test_regr.to_dict())

    def test_regression_doc_from_json_missing_key(self):
        test_regr = {
            "_id": "id",
        }
        self.assertIsNone(mtregr.TestRegressionDocument.from_json(test_regr))

    def test_regression_doc_from_json_wrong_type(self):
        self.assertIsNone(mtregr.TestRegressionDocument.from_json([]))
        self.assertIsNone(mtregr.TestRegressionDocument.from_json(()))
        self.assertIsNone(mtregr.TestRegressionDocument.from_json(""))

    def test_regression_doc_from_json(self):
        regr_json = {
            "_id": "id",
            "version": "1.0",
            "job": "full-time",
            "kernel": "linux-1.0",
            "git_branch": "some-branch",
            "git_url": "some-url",
            "defconfig_full": "allnoconfig+random",
            "build_environment": "concrete",
            "device_type": "dev-board",
            "arch": "bips",
            "hierarchy": ["suite", "group", "case"],
            "plan": "suite",
            "test_case_path": "suite.group.case",
            "compiler": None,
            "compiler_version": None,
            "regressions": [
                {
                    "test_case_id": "test-case-id",
                    "created_on": "now",
                    "status": "PASS",
                    "kernel": "kernel-001",
                    "git_commit": "1234abcd",
                    "lab_name": "secret-lab",
                    "build_id": "some-build-id",
                    "plan_variant": "cunning",
                },
                {
                    "test_case_id": "another-test-case-id",
                    "created_on": "later",
                    "status": "PASS",
                    "kernel": "kernel-002",
                    "git_commit": "1234abce",
                    "lab_name": "secret-lab",
                    "build_id": "some-build-id",
                    "plan_variant": "cunning",
                },
            ],
        }

        test_regr = mtregr.TestRegressionDocument.from_json(regr_json)
        self.assertIsInstance(test_regr, mtregr.TestRegressionDocument)
        test_regr._created_on = regr_json["created_on"] = "tomorrow"
        self.assertDictEqual(regr_json, test_regr.to_dict())
