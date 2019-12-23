# Copyright (C) Collabora Limited 2018,2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
#
# Copyright (C) Linaro Limited 2014,2015,2017
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

import models.base as modb
import models.bisect as modbs


class TestBisectModel(unittest.TestCase):

    def test_bisect_base_document(self):
        bisect_doc = modbs.BisectDocument()
        self.assertIsInstance(bisect_doc, modb.BaseDocument)

    def test_boot_bisect_document(self):
        bisect_doc = modbs.BootBisectDocument()
        self.assertIsInstance(bisect_doc, modbs.BisectDocument)
        self.assertIsInstance(bisect_doc, modb.BaseDocument)

    def test_bisect_base_document_collection(self):
        bisect_doc = modbs.BisectDocument()
        self.assertEqual(bisect_doc.collection, "bisect")

    def test_bisect_boot_document_collection(self):
        bisect_doc = modbs.BootBisectDocument()
        self.assertEqual(bisect_doc.collection, "bisect")

    def test_bisect_base_from_json(self):
        bisect_doc = modbs.BisectDocument()

        self.assertIsNone(bisect_doc.from_json({}))
        self.assertIsNone(bisect_doc.from_json([]))
        self.assertIsNone(bisect_doc.from_json(()))
        self.assertIsNone(bisect_doc.from_json(""))

    def test_bisect_base_to_dict(self):
        bisect_doc = modbs.BisectDocument()

        expected = {
            "created_on": None,
            "job": None,
            "bisect_data": [],
            "compare_to": None,
            "good_commit": None,
            "good_commit_date": None,
            "good_commit_url": None,
            "good_summary": None,
            "bad_commit": None,
            "bad_commit_date": None,
            "bad_commit_url": None,
            "bad_summary": None,
            "version": None,
            "job_id": None,
            "type": None,
            "found_summary": None,
            "kernel": None,
            "log": None,
            "checks": {},
            "arch": None,
            "build_id": None,
            "defconfig": None,
            "defconfig_full": None,
            "compiler": None,
            "compiler_version": None,
            "build_environment": None,
            "git_branch": None,
            "git_url": None,
            "plan": None,
            "plan_variant": None,
        }
        self.assertDictEqual(expected, bisect_doc.to_dict())

    def test_bisect_base_to_dict_with_id(self):
        bisect_doc = modbs.BisectDocument()
        bisect_doc.id = "bar"

        expected = {
            "_id": "bar",
            "created_on": None,
            "job": None,
            "bisect_data": [],
            "compare_to": None,
            "good_commit": None,
            "good_commit_date": None,
            "good_commit_url": None,
            "good_summary": None,
            "bad_commit": None,
            "bad_commit_date": None,
            "bad_commit_url": None,
            "bad_summary": None,
            "version": None,
            "job_id": None,
            "type": None,
            "found_summary": None,
            "kernel": None,
            "log": None,
            "checks": {},
            "arch": None,
            "build_id": None,
            "defconfig": None,
            "defconfig_full": None,
            "compiler": None,
            "compiler_version": None,
            "build_environment": None,
            "git_branch": None,
            "git_url": None,
            "plan": None,
            "plan_variant": None,
        }
        self.assertDictEqual(expected, bisect_doc.to_dict())

    def test_bisect_boot_to_dict(self):
        bisect_doc = modbs.BootBisectDocument()
        bisect_doc.id = "bar"
        bisect_doc.board = "baz"
        bisect_doc.version = "1.0"
        bisect_doc.boot_id = "boot-id"
        bisect_doc.build_id = "build-id"
        bisect_doc.job_id = "job-id"
        bisect_doc.git_url = "https://somewhere.com/blah.git"
        bisect_doc.git_branch = "master"
        bisect_doc.kernel = "v123.456"
        bisect_doc.log = "https://storage.org/log.txt"
        bisect_doc.device_type = "qemu"
        bisect_doc.lab_name = "secret-lab"
        bisect_doc.plan = "cunning"

        expected = {
            "_id": "bar",
            "board": "baz",
            "created_on": None,
            "job": None,
            "bisect_data": [],
            "compare_to": None,
            "good_commit": None,
            "good_commit_date": None,
            "good_commit_url": None,
            "good_summary": None,
            "bad_commit": None,
            "bad_commit_date": None,
            "bad_commit_url": None,
            "bad_summary": None,
            "version": "1.0",
            "boot_id": "boot-id",
            "build_id": "build-id",
            "job_id": "job-id",
            "type": "boot",
            "compiler": None,
            "compiler_version": None,
            "build_environment": None,
            "lab_name": "secret-lab",
            "arch": None,
            "device_type": "qemu",
            "defconfig": None,
            "defconfig_full": None,
            "git_url": "https://somewhere.com/blah.git",
            "git_branch": "master",
            "kernel": "v123.456",
            "log": "https://storage.org/log.txt",
            "found_summary": None,
            "checks": {},
            "plan": "cunning",
            "plan_variant": None,
        }
        self.assertDictEqual(expected, bisect_doc.to_dict())

    def test_bisect_base_properties(self):
        bisect_doc = modbs.BootBisectDocument()
        bisect_doc.id = "bar"
        bisect_doc.created_on = "now"
        bisect_doc.job = "fooz"
        bisect_doc.bisect_data = [1, 2, 3]
        bisect_doc.good_commit = "1"
        bisect_doc.good_commit_date = "now"
        bisect_doc.good_commit_url = "url"
        bisect_doc.bad_commit = "2"
        bisect_doc.bad_commit_date = "now"
        bisect_doc.bad_commit_url = "url"
        bisect_doc.found_summary = "1234abcd foo: bar"
        bisect_doc.verified = "pass"
        bisect_doc.kernel = "v456.789"
        bisect_doc.log = "https://storage.org/log.txt"

        self.assertEqual(bisect_doc.id, "bar")
        self.assertEqual(bisect_doc.created_on, "now")
        self.assertEqual(bisect_doc.job, "fooz")
        self.assertEqual(bisect_doc.bisect_data, [1, 2, 3])
        self.assertEqual(bisect_doc.good_commit, "1")
        self.assertEqual(bisect_doc.good_commit_date, "now")
        self.assertEqual(bisect_doc.good_commit_url, "url")
        self.assertEqual(bisect_doc.bad_commit, "2")
        self.assertEqual(bisect_doc.bad_commit_date, "now")
        self.assertEqual(bisect_doc.bad_commit_url, "url")
        self.assertEqual(bisect_doc.found_summary, "1234abcd foo: bar")
        self.assertEqual(bisect_doc.verified, "pass")
        self.assertEqual(bisect_doc.kernel, "v456.789")
        self.assertEqual(bisect_doc.log, "https://storage.org/log.txt")

    def test_bisect_boot_properties(self):
        bisect_doc = modbs.BootBisectDocument()
        bisect_doc.board = "bar"

        self.assertEqual(bisect_doc.board, "bar")

    def test_bisect_defconfig_to_dict(self):
        bisect_doc = modbs.DefconfigBisectDocument()
        bisect_doc.id = "bar"
        bisect_doc.build_id = "build-id"
        bisect_doc.defconfig = "defconfig-name"
        bisect_doc.version = "1.0"
        bisect_doc.job = "job"
        bisect_doc.job_id = "job-id"
        bisect_doc.defconfig_full = "defconfig-full"
        bisect_doc.arch = "arm"
        bisect_doc.found_summary = "7890cdef foo: change bar into baz"
        bisect_doc.kernel = "v4.56"
        bisect_doc.git_url = "https://somewhere.com/blah.git"
        bisect_doc.compiler = "randomcc"
        bisect_doc.compiler_version = "123.456"
        bisect_doc.build_environment = "build-env"
        bisect_doc.plan = "cunning"
        bisect_doc.plan_variant = "similar"

        expected = {
            "_id": "bar",
            "created_on": None,
            "job": "job",
            "bisect_data": [],
            "compare_to": None,
            "good_commit": None,
            "good_commit_date": None,
            "good_commit_url": None,
            "good_summary": None,
            "bad_commit": None,
            "bad_commit_date": None,
            "bad_commit_url": None,
            "bad_summary": None,
            "version": "1.0",
            "build_id": "build-id",
            "defconfig": "defconfig-name",
            "job_id": "job-id",
            "defconfig_full": "defconfig-full",
            "compiler": "randomcc",
            "compiler_version": "123.456",
            "build_environment": "build-env",
            "arch": "arm",
            "type": "build",
            "git_branch": None,
            "found_summary": "7890cdef foo: change bar into baz",
            "git_url": "https://somewhere.com/blah.git",
            "kernel": "v4.56",
            "log": None,
            "checks": {},
            "plan": "cunning",
            "plan_variant": "similar",
        }

        self.assertDictEqual(expected, bisect_doc.to_dict())
