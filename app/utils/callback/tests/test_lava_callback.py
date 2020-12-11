# Copyright (C) Collabora Limited 2020
# Author: Michal Galka <michal.galka@collabora.com>
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

import json
import mock
import mongomock
import os
import unittest
import yaml

from utils.callback.lava import add_tests


class TestLavaCallback(unittest.TestCase):
    def _load_callback_json(self, filename, data_path):
        with open(os.path.join(data_path, filename), 'r') as callback_file:
            data = json.load(callback_file, encoding='utf8')
        return data

    def _get_json_obj_and_meta(self, filename, data_path=None):
        if data_path is None:
            data_path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)),
                'data')
        json_obj = self._load_callback_json(filename, data_path)
        definition = yaml.load(json_obj["definition"], Loader=yaml.CLoader)
        job_meta = definition.get("metadata")
        return json_obj, job_meta

    @mock.patch('utils.db.get_db_connection')
    def test_login_test_case_exists_autologin(self, mock_db_connection):
        connection = mongomock.MongoClient()['mock-kernel-ci']
        mock_db_connection.return_value = connection
        json_obj, job_meta = self._get_json_obj_and_meta(
            'auto-login-action.json')
        add_tests(json_obj, job_meta, 'dummy-lab', {}, '/tmp')
        self.assertTrue(
            [data for data in connection.test_case.find({'name': 'login'})])

    @mock.patch('utils.db.get_db_connection')
    def test_login_test_case_exists_login(self, mock_db_connection):
        connection = mongomock.MongoClient()['mock-kernel-ci']
        mock_db_connection.return_value = connection
        json_obj, job_meta = self._get_json_obj_and_meta(
            'login-action.json')
        add_tests(json_obj, job_meta, 'dummy-lab', {}, '/tmp')
        self.assertTrue(
            [data for data in connection.test_case.find({'name': 'login'})])

    @mock.patch('utils.db.get_db_connection')
    def test_login_test_case_status_boot_fail(self, mock_db_connection):
        connection = mongomock.MongoClient()['mock-kernel-ci']
        mock_db_connection.return_value = connection
        json_obj, job_meta = self._get_json_obj_and_meta(
            'unhandled_fault-login-status.json')
        add_tests(json_obj, job_meta, 'dummy-lab', {}, '/tmp')
        login_test_case = connection.test_case.find_one({'name': 'login'})
        self.assertEqual(login_test_case['status'], 'FAIL')

    @mock.patch('utils.db.get_db_connection')
    def test_no_boot_loglines_attached(self, mock_db_connection):
        connection = mongomock.MongoClient()['mock-kernel-ci']
        mock_db_connection.return_value = connection
        json_obj, job_meta = self._get_json_obj_and_meta(
            'lava-json-jetson-tk1.json')
        add_tests(json_obj, job_meta, 'dummy-lab', {}, '/tmp')
        boot_loglines_present = False
        for tc in connection.test_case.find():
            for log_line in tc['log_lines']:
                if 'Starting kernel ...' in log_line['msg']:
                    boot_loglines_present = True
        self.assertFalse(boot_loglines_present)

    @mock.patch('utils.db.get_db_connection')
    def test_log_fragment_present(self, mock_db_connection):
        connection = mongomock.MongoClient()['mock-kernel-ci']
        mock_db_connection.return_value = connection
        json_obj, job_meta = self._get_json_obj_and_meta(
            'lava-json-meson-gxbb-p200.json')
        add_tests(json_obj, job_meta, 'dummy-lab', {}, '/tmp')
        log_lines = connection.test_case.find_one(
            {'test_case_path': 'baseline.dmesg.emerg'})['log_lines']
        self.assertGreater(len(log_lines), 0)
