# Copyright (C) Linaro Limited 2014,2015,2017,2018
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

"""Test module for the BootHandler handler."""

try:
    import simplejson as json
except ImportError:
    import json

import mock
import tornado

import urls

from handlers.tests.test_handler_base import TestHandlerBase


class TestBootHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application(
            [urls._BOOT_URL, urls._BOOT_ID_URL], **self.settings)

    def test_post_wrong_content(self):
        body = {"foo": "bar"}
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/boot", method="POST", body=json.dumps(body), headers=headers)

        self.assertEqual(response.code, 400)

    @mock.patch("taskqueue.tasks.boot.import_boot")
    @mock.patch("utils.db.find_one2")
    def test_post_valid_content_same_token(self, find_one, import_boot):
        self.req_token.token = "foo"
        find_one.side_effect = [
            {"name": "lab-name", "token": "id-token"},
            {
                "_id": "id-token",
                "token": "foo", "expired": False, "email": "email@example.net"
            }
        ]
        body = {
            "version": "1.0",
            "board": "board",
            "job": "job",
            "kernel": "kernel",
            "defconfig": "defconfig",
            "lab_name": "lab-name",
            "git_branch": "branch",
            "arch": "arm",
            "build_environment": "build_environment"
        }
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/boot", method="POST", body=json.dumps(body), headers=headers)

        self.assertEqual(response.code, 202)

    @mock.patch("utils.db.find_one2")
    def test_post_valid_content_different_token(self, find_one):
        find_one.side_effect = [
            {"token": "bar"},
            {
                "token": "bar",
                "expired": False,
                "email": "email@example.net", "_id": "token-id"
            }
        ]
        body = {
            "version": "1.0",
            "board": "board",
            "job": "job",
            "kernel": "kernel",
            "defconfig": "defconfig",
            "lab_name": "lab-name",
            "git_branch": "branch",
            "arch": "arm",
            "build_environment": "build_environment"
        }
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/boot", method="POST", body=json.dumps(body), headers=headers)

        self.assertEqual(response.code, 403)

    @mock.patch("taskqueue.tasks.boot.import_boot")
    @mock.patch("utils.db.find_one2")
    def test_post_valid_content_different_token_admin(
            self, find_one, import_boot):
        self.req_token.is_admin = True

        find_one.side_effect = [
            {"token": "id-lab-token", "name": "lab-name"},
            {"_id": "id-lab-token", "token": "bar"}
        ]
        body = {
            "version": "1.0",
            "board": "board",
            "job": "job",
            "kernel": "kernel",
            "defconfig": "defconfig",
            "lab_name": "lab-name",
            "git_branch": "branch",
            "arch": "arm",
            "build_environment": "build_environment"
        }
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/boot", method="POST", body=json.dumps(body), headers=headers)

        self.assertEqual(response.code, 202)

    def test_post_valid_content_expired_req_token(self):
        self.req_token.expired = True
        body = {
            "version": "1.0",
            "board": "board",
            "job": "job",
            "kernel": "kernel",
            "defconfig": "defconfig",
            "lab_name": "lab-name",
            "git_branch": "branch",
            "arch": "arm",
            "build_environment": "build_environment"
        }
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/boot", method="POST", body=json.dumps(body), headers=headers)

        self.assertEqual(response.code, 403)
