# Copyright (C) Collabora Limited 2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
#
# Copyright (C) Linaro Limited 2015,2016,2017,2018
# Author: Matt Hart <matthew.hart@linaro.org>
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

try:
    import simplejson as json
except ImportError:
    import json

import io
import logging
import mock
import mongomock
import os
import pymongo.errors
import shutil
import tempfile
import types
import unittest

import models.build as mbuild
import models.job as mjob
import utils.build
from utils.build.tests import SAMPLE_META


class TestBuildUtils(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.db = mongomock.Database(mongomock.MongoClient(),
                                     "kernel-ci", None)

        patcher = mock.patch("utils.database.redisdb.get_db_connection")
        mock_open = patcher.start()
        mock_open.return_value = mock.MagicMock()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_update_job_doc(self):
        job_doc = mjob.JobDocument("job", "kernel", "branch")
        build_doc = mbuild.BuildDocument(
            "job", "kernel", "defconfig", "branch", "build_environment")
        build_doc.git_branch = "branch"
        build_doc.git_commit = "1234567890"
        build_doc.git_describe = "kernel.version"
        build_doc.git_url = "git://url.git"

        utils.build._update_job_doc(
            job_doc, "job_id", "PASS", build_doc, self.db)

        self.assertIsInstance(job_doc, mjob.JobDocument)
        self.assertIsNotNone(job_doc.id)
        self.assertIsNotNone(job_doc.git_branch)
        self.assertIsNotNone(job_doc.git_commit)
        self.assertIsNotNone(job_doc.git_describe)
        self.assertIsNotNone(job_doc.git_url)
        self.assertEqual("job_id", job_doc.id)
        self.assertEqual("1234567890", job_doc.git_commit)
        self.assertEqual("kernel.version", job_doc.git_describe)
        self.assertEqual("git://url.git", job_doc.git_url)

    def test_update_job_doc_no_defconfig(self):
        job_doc = mjob.JobDocument("job", "kernel", "branch")

        utils.build._update_job_doc(
            job_doc, None, "PASS", None, self.db)

        self.assertIsInstance(job_doc, mjob.JobDocument)
        self.assertIsNotNone(job_doc.git_branch)
        self.assertIsNone(job_doc.id)
        self.assertIsNone(job_doc.git_commit)
        self.assertIsNone(job_doc.git_describe)
        self.assertIsNone(job_doc.git_url)

    @mock.patch("utils.db.get_db_connection")
    @mock.patch("utils.db.save")
    @mock.patch("utils.build._update_job_doc")
    @mock.patch("utils.db.find_one2")
    @mock.patch("os.path.isdir")
    def test_import_single_build(
            self, mock_dir, mock_find, mock_up, mock_save, mock_db):
        mock_db = self.db
        mock_dir.return_value = True

        job_doc = {
            "job": "ajob",
            "kernel": "kernel",
            "_id": "job_id",
            "git_branch": "branch"
        }
        build_doc = mbuild.BuildDocument(
            "job", "kernel", "defconfig", "branch", "build_environment")
        build_doc.git_branch = "branch"

        mock_find.return_value = job_doc
        mock_up.return_value = 201
        mock_save.return_value = (201, "build_id")

        build_id, job_id, errors = utils.build.import_single_build(
            SAMPLE_META, {})

        self.assertDictEqual({}, errors)
        self.assertIsNotNone(build_id)
        self.assertIsNotNone(job_id)
        self.assertEqual("build_id", build_id)
        self.assertEqual("job_id", job_id)
