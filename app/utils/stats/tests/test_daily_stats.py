# Copyright (C) Linaro Limited 2015
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

import datetime
import logging
import mock
import mongomock
import unittest

import utils.stats.daily


class TestDailyStats(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.db = mongomock.Database(mongomock.MongoClient(),
                                     "kernel-ci", None)
        self.today = datetime.datetime(
            2015, 8, 10, hour=0, minute=1, second=0, microsecond=0)

        patcher = mock.patch("utils.db.get_db_connection")
        patched_db = patcher.start()
        patched_db.return_value = self.db
        self.addCleanup(patcher.stop)

        date_patcher = mock.patch("datetime.datetime", spec=True)
        patched_date = date_patcher.start()
        patched_date.now = mock.MagicMock()
        patched_date.now.return_value = self.today
        self.addCleanup(date_patcher.stop)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @mock.patch("utils.stats.daily.get_start_date")
    @mock.patch("utils.stats.daily.calculate_build_stats")
    @mock.patch("utils.stats.daily.calculate_job_stats")
    def test_calculate_daily_empty(
            self, mock_job, mock_build, mock_start):
        mock_job.return_value = {}
        mock_build.return_value = {}
        mock_start.return_value = "yesterday"

        expected = {
            "biweekly_total_builds": 0,
            "biweekly_total_jobs": 0,
            "biweekly_unique_archs": 0,
            "biweekly_unique_boards": 0,
            "biweekly_unique_kernels": 0,
            "biweekly_unique_machs": 0,
            "biweekly_unique_trees": 0,
            "biweekly_unique_defconfigs": 0,
            "created_on": self.today,
            "daily_total_builds": 0,
            "daily_total_jobs": 0,
            "daily_unique_archs": 0,
            "daily_unique_boards": 0,
            "daily_unique_kernels": 0,
            "daily_unique_machs": 0,
            "daily_unique_trees": 0,
            "daily_unique_defconfigs": 0,
            "start_date": "yesterday",
            "total_builds": 0,
            "total_jobs": 0,
            "total_unique_archs": 0,
            "total_unique_boards": 0,
            "total_unique_kernels": 0,
            "total_unique_machs": 0,
            "total_unique_trees": 0,
            "total_unique_defconfigs": 0,
            "version": "1.0",
            "weekly_total_builds": 0,
            "weekly_total_jobs": 0,
            "weekly_unique_archs": 0,
            "weekly_unique_boards": 0,
            "weekly_unique_kernels": 0,
            "weekly_unique_machs": 0,
            "weekly_unique_trees": 0,
            "weekly_unique_defconfigs": 0
        }

        daily_stats = utils.stats.daily.calculate_daily_stats({})
        self.assertDictEqual(expected, daily_stats.to_dict())

    @mock.patch("utils.stats.daily.get_start_date")
    @mock.patch("utils.stats.daily.calculate_build_stats")
    @mock.patch("utils.stats.daily.calculate_job_stats")
    def test_calculate_daily_with_job(
            self, mock_job, mock_build, mock_date):
        mock_build.return_value = {}
        mock_date.return_value = "yesterday"
        mock_job.return_value = {
            "biweekly_total_jobs": 10,
            "biweekly_unique_kernels": 1024,
            "biweekly_unique_trees": 1,
            "daily_total_jobs": 500,
            "daily_unique_kernels": 20,
            "daily_unique_trees": 100,
            "total_jobs": 1000,
            "total_unique_kernels": 20,
            "total_unique_trees": 100,
            "weekly_total_jobs": 10,
            "weekly_unique_kernels": 1,
            "weekly_unique_trees": 100
        }

        expected = {
            "biweekly_total_builds": 0,
            "biweekly_total_jobs": 10,
            "biweekly_unique_archs": 0,
            "biweekly_unique_boards": 0,
            "biweekly_unique_kernels": 1024,
            "biweekly_unique_machs": 0,
            "biweekly_unique_trees": 1,
            "biweekly_unique_defconfigs": 0,
            "created_on": self.today,
            "daily_total_builds": 0,
            "daily_total_jobs": 500,
            "daily_unique_archs": 0,
            "daily_unique_boards": 0,
            "daily_unique_kernels": 20,
            "daily_unique_machs": 0,
            "daily_unique_trees": 100,
            "daily_unique_defconfigs": 0,
            "start_date": "yesterday",
            "total_builds": 0,
            "total_jobs": 1000,
            "total_unique_archs": 0,
            "total_unique_boards": 0,
            "total_unique_kernels": 20,
            "total_unique_machs": 0,
            "total_unique_trees": 100,
            "total_unique_defconfigs": 0,
            "version": "1.0",
            "weekly_total_builds": 0,
            "weekly_total_jobs": 10,
            "weekly_unique_archs": 0,
            "weekly_unique_boards": 0,
            "weekly_unique_kernels": 1,
            "weekly_unique_machs": 0,
            "weekly_unique_trees": 100,
            "weekly_unique_defconfigs": 0
        }

        daily_stats = utils.stats.daily.calculate_daily_stats({})
        self.assertDictEqual(expected, daily_stats.to_dict())

    @mock.patch("utils.stats.daily.get_start_date")
    @mock.patch("utils.stats.daily.calculate_build_stats")
    @mock.patch("utils.stats.daily.calculate_job_stats")
    def test_calculate_daily_with_build(
            self, mock_job, mock_build, mock_start):
        mock_job.return_value = {}
        mock_start.return_value = "yesterday"
        mock_build.return_value = {
            "biweekly_total_builds": 1,
            "biweekly_unique_defconfigs": 1,
            "daily_total_builds": 10,
            "daily_unique_defconfigs": 10,
            "total_builds": 1024,
            "total_unique_defconfigs": 10,
            "weekly_total_builds": 10,
            "weekly_unique_defconfigs": 10
        }

        expected = {
            "biweekly_total_builds": 1,
            "biweekly_total_jobs": 0,
            "biweekly_unique_archs": 0,
            "biweekly_unique_boards": 0,
            "biweekly_unique_kernels": 0,
            "biweekly_unique_machs": 0,
            "biweekly_unique_trees": 0,
            "biweekly_unique_defconfigs": 1,
            "created_on": self.today,
            "daily_total_builds": 10,
            "daily_total_jobs": 0,
            "daily_unique_archs": 0,
            "daily_unique_boards": 0,
            "daily_unique_kernels": 0,
            "daily_unique_machs": 0,
            "daily_unique_trees": 0,
            "daily_unique_defconfigs": 10,
            "start_date": "yesterday",
            "total_builds": 1024,
            "total_jobs": 0,
            "total_unique_archs": 0,
            "total_unique_boards": 0,
            "total_unique_kernels": 0,
            "total_unique_machs": 0,
            "total_unique_trees": 0,
            "total_unique_defconfigs": 10,
            "version": "1.0",
            "weekly_total_builds": 10,
            "weekly_total_jobs": 0,
            "weekly_unique_archs": 0,
            "weekly_unique_boards": 0,
            "weekly_unique_kernels": 0,
            "weekly_unique_machs": 0,
            "weekly_unique_trees": 0,
            "weekly_unique_defconfigs": 10
        }

        daily_stats = utils.stats.daily.calculate_daily_stats({})
        self.assertDictEqual(expected, daily_stats.to_dict())
