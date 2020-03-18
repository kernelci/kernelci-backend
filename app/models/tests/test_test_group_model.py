# Copyright (C) Collabora Limited 2018,2019
# Author: Michal Galka <michal.galka@collabora.com>
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
#
# Copyright (C) Linaro Limited 2019
# Author: Matt Hart <matthew.hart@linaro.org>
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

import models.base as mbase
import models.test_group as mtgroup


class TestTestGroupModel(unittest.TestCase):

    def test_group_doc_valid_instance(self):
        test_group = mtgroup.TestGroupDocument("name", "lab-name")
        self.assertIsInstance(test_group, mbase.BaseDocument)

    def test_group_doc_to_dict(self):
        test_group = mtgroup.TestGroupDocument("name", "lab-name")

        test_group.arch = "arm"
        test_group.board = "board"
        test_group.board_instance = 1
        test_group.boot_log = "boot-log"
        test_group.boot_log_html = "boot-log-html"
        test_group.boot_result_description = "boot-result-description"
        test_group.build_environment = "build-environment"
        test_group.build_id = "build-id"
        test_group.compiler = "gcc"
        test_group.compiler_version = "4.7.3"
        test_group.compiler_version_full = "gcc version 4.7.3"
        test_group.created_on = "now"
        test_group.cross_compile = "cross-compile"
        test_group.defconfig = "defconfig"
        test_group.defconfig_full = "defconfig-full"
        test_group.device_type = "device-type"
        test_group.dtb = "dtb"
        test_group.endian = "big-endian"
        test_group.file_server_resource = "file-resource"
        test_group.git_branch = "git-branch"
        test_group.git_commit = "git-commit"
        test_group.git_describe = "git-describe"
        test_group.git_url = "git-url"
        test_group.id = "id"
        test_group.index = 1
        test_group.image_type = "image_type"
        test_group.initrd = "initrd"
        test_group.initrd_info = "initrd-info"
        test_group.job = "job"
        test_group.job_id = "job_id"
        test_group.kernel = "kernel"
        test_group.kernel_image = "kernel-image"
        test_group.mach = "mach"
        test_group.modules = "moduli"
        test_group.parent_id = "parent-id"
        test_group.plan_variant = "tother"
        test_group.sub_groups = [True, False]
        test_group.test_cases = ["foo"]
        test_group.time = 10
        test_group.version = "1.1"
        test_group.warnings = 123

        expected = {
            "_id": "id",
            "arch": "arm",
            "board": "board",
            "board_instance": 1,
            "boot_log": "boot-log",
            "boot_log_html": "boot-log-html",
            "boot_result_description": "boot-result-description",
            "build_environment": "build-environment",
            "build_id": "build-id",
            "compiler": "gcc",
            "compiler_version": "4.7.3",
            "compiler_version_full": "gcc version 4.7.3",
            "created_on": "now",
            "cross_compile": "cross-compile",
            "defconfig": "defconfig",
            "defconfig_full": "defconfig-full",
            "device_type": "device-type",
            "dtb": "dtb",
            "endian": "big-endian",
            "file_server_resource": "file-resource",
            "git_branch": "git-branch",
            "git_commit": "git-commit",
            "git_describe": "git-describe",
            "git_url": "git-url",
            "image_type": "image_type",
            "index": 1,
            "initrd": "initrd",
            "initrd_info": "initrd-info",
            "job": "job",
            "job_id": "job_id",
            "kernel": "kernel",
            "kernel_image": "kernel-image",
            "lab_name": "lab-name",
            "mach": "mach",
            "modules": "moduli",
            "parent_id": "parent-id",
            "plan_variant": "tother",
            "name": "name",
            "sub_groups": [True, False],
            "test_cases": ["foo"],
            "time": 10,
            "version": "1.1",
            "warnings": 123,
        }

        self.assertDictEqual(expected, test_group.to_dict())

    def test_group_doc_from_json_missing_key(self):
        test_group = {
            "_id": "id"
        }

        self.assertIsNone(mtgroup.TestGroupDocument.from_json(test_group))

    def test_group_doc_from_json_wrong_type(self):
        self.assertIsNone(mtgroup.TestGroupDocument.from_json([]))
        self.assertIsNone(mtgroup.TestGroupDocument.from_json(()))
        self.assertIsNone(mtgroup.TestGroupDocument.from_json(""))

    def test_group_doc_from_json(self):
        self.maxDiff = None
        group_json = {
            "_id": "id",
            "arch": "arm",
            "board": "board",
            "board_instance": 1,
            "boot_log": None,
            "boot_log_html": None,
            "boot_result_description": None,
            "build_environment": "build-environment",
            "build_id": "build-id",
            "compiler": None,
            "compiler_version": None,
            "compiler_version_full": None,
            "created_on": "now",
            "cross_compile": None,
            "defconfig": "defconfig",
            "defconfig_full": "defconfig",
            "device_type": "device-type",
            "dtb": None,
            "endian": None,
            "file_server_resource": None,
            "git_branch": "git_branch",
            "git_commit": "git_commit",
            "git_describe": "git_describe",
            "git_url": "git_url",
            "initrd": "initrd",
            "index": 1,
            "image_type": "image_type",
            "initrd_info": None,
            "job": "job",
            "job_id": "job_id",
            "kernel": "kernel",
            "kernel_image": None,
            "lab_name": "lab-name",
            "mach": "mach",
            "modules": "modules",
            "name": "name",
            "parent_id": "parent-id",
            "plan_variant": "tother",
            "sub_groups": [True, False],
            "test_cases": ["foo"],
            "time": 10,
            "version": "1.0",
            "warnings": 123,
        }

        test_group = mtgroup.TestGroupDocument.from_json(group_json)

        self.assertIsInstance(test_group, mtgroup.TestGroupDocument)
        self.assertDictEqual(group_json, test_group.to_dict())
