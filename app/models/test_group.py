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

"""The model that represent a test group document in the database."""

import copy
import types

import models
import models.base as modb


# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes
class TestGroupDocument(modb.BaseDocument):
    """Model for a test group document.

    A test group is a document that can store test cases results, and nested
    test groups.
    """

    def __init__(self, name, lab_name):
        """The test group document.

        :param name: The name given to this test group.
        :type name: string
        :param lab_name: The name of the lab running this test group.
        :type lab_name: str
        """
        self._name = name
        self._lab_name = lab_name
        self._build_id = None
        self._version = None
        self._id = None
        self._created_on = None

        self.arch = None
        self.board_instance = None
        self.boot_log = None
        self.boot_log_html = None
        self.boot_result_description = None
        self.build_environment = None
        self.compiler = None
        self.compiler_version = None
        self.compiler_version_full = None
        self.cross_compile = None
        self.defconfig = None
        self.defconfig_full = None
        self.device_type = None
        self.dtb = None
        self.endian = None
        self.file_server_resource = None
        self.git_branch = None
        self.git_commit = None
        self.git_describe = None
        self.git_url = None
        self.index = None
        self.initrd = None
        self.initrd_info = None
        self.job = None
        self.job_id = None
        self.kernel = None
        self.kernel_image = None
        self.mach = None
        self.modules = None
        self.plan_variant = None
        self.test_cases = []
        self.parent_id = None
        self.sub_groups = []
        self.time = -1
        self.warnings = 0

    @property
    def collection(self):
        return models.TEST_GROUP_COLLECTION

    @property
    def name(self):
        """The name of the test group."""
        return self._name

    @property
    def lab_name(self):
        """The name of the test lab."""
        return self._lab_name

    @property
    def build_id(self):
        """The ID of the build."""
        return self._build_id

    @build_id.setter
    def build_id(self, value):
        """Set the ID of the build."""
        if self._build_id:
            raise AttributeError("Build ID already set")
        self._build_id = value

    @property
    def version(self):
        """The schema version of this test group."""
        return self._version

    @version.setter
    def version(self, value):
        """Set the schema version of this test group."""
        if self._version:
            raise AttributeError("Schema version already set")
        self._version = value

    @property
    def id(self):
        """The ID of the test group as registered in the database."""
        return self._id

    @id.setter
    def id(self, value):
        """Set the test group ID."""
        if self._id:
            raise AttributeError("ID already set")
        self._id = value

    @property
    def created_on(self):
        """The creation date of this test group."""
        return self._created_on

    @created_on.setter
    def created_on(self, value):
        """Set the creation date of this test group."""
        if self._created_on:
            raise AttributeError("Creation date already set")
        self._created_on = value

    def to_dict(self):
        test_group = {
            models.ARCHITECTURE_KEY: self.arch,
            models.BOARD_INSTANCE_KEY: self.board_instance,
            models.BOOT_LOG_KEY: self.boot_log,
            models.BOOT_LOG_HTML_KEY: self.boot_log_html,
            models.BOOT_RESULT_DESC_KEY: self.boot_result_description,
            models.BUILD_ENVIRONMENT_KEY: self.build_environment,
            models.BUILD_ID_KEY: self.build_id,
            models.COMPILER_KEY: self.compiler,
            models.COMPILER_VERSION_FULL_KEY: self.compiler_version_full,
            models.COMPILER_VERSION_KEY: self.compiler_version,
            models.CROSS_COMPILE_KEY: self.cross_compile,
            models.CREATED_KEY: self.created_on,
            models.DEFCONFIG_FULL_KEY: self.defconfig_full or self.defconfig,
            models.DEFCONFIG_KEY: self.defconfig,
            models.DEVICE_TYPE_KEY: self.device_type,
            models.DTB_KEY: self.dtb,
            models.ENDIANNESS_KEY: self.endian,
            models.FILE_SERVER_RESOURCE_KEY: self.file_server_resource,
            models.GIT_BRANCH_KEY: self.git_branch,
            models.GIT_COMMIT_KEY: self.git_commit,
            models.GIT_DESCRIBE_KEY: self.git_describe,
            models.GIT_URL_KEY: self.git_url,
            models.INDEX_KEY: self.index,
            models.INITRD_KEY: self.initrd,
            models.INITRD_INFO_KEY: self.initrd_info,
            models.JOB_ID_KEY: self.job_id,
            models.JOB_KEY: self.job,
            models.KERNEL_KEY: self.kernel,
            models.KERNEL_IMAGE_KEY: self.kernel_image,
            models.LAB_NAME_KEY: self.lab_name,
            models.MACH_KEY: self.mach,
            models.MODULES_KEY: self.modules,
            models.NAME_KEY: self.name,
            models.PLAN_VARIANT_KEY: self.plan_variant,
            models.TEST_CASES_KEY: self.test_cases,
            models.PARENT_ID_KEY: self.parent_id,
            models.SUB_GROUPS_KEY: self.sub_groups,
            models.TIME_KEY: self.time,
            models.VERSION_KEY: self.version,
            models.WARNINGS_KEY: self.warnings,
        }

        if self.id:
            test_group[models.ID_KEY] = self.id

        return test_group

    @staticmethod
    def from_json(json_obj):
        test_group = None
        if isinstance(json_obj, types.DictionaryType):
            local_obj = copy.deepcopy(json_obj)
            doc_pop = local_obj.pop

            try:
                name = doc_pop(models.NAME_KEY)
                lab_name = doc_pop(models.LAB_NAME_KEY)
                test_group = TestGroupDocument(name, lab_name)
                for key, val in local_obj.iteritems():
                    setattr(test_group, key, val)
            except KeyError:
                # Missing mandatory key? Return None.
                test_group = None

        return test_group
