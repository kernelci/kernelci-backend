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

"""Test module for the UploadHandler."""

import tornado

import urls

from handlers.tests.test_handler_base import TestHandlerBase


class TestUploadHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application([urls._UPLOAD_URL], **self.settings)

    def test_get(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/upload", method="GET", headers=headers)

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_no_token(self):
        response = self.fetch("/upload", method="GET")
        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/upload", method="DELETE", headers=headers)

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete_no_token(self):
        response = self.fetch("/upload", method="DELETE")
        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_no_token(self):
        response = self.fetch("/upload", method="POST", body="")
        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_token_wrong_content(self):
        headers = {
            "Authorization": "foo",
            "Content-Type": "application/json"
        }
        response = self.fetch(
            "/upload", method="POST", body="", headers=headers)
        self.assertEqual(response.code, 415)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_token_missing_content(self):
        headers = {
            "Authorization": "foo"
        }
        response = self.fetch(
            "/upload", method="POST", body="", headers=headers)
        self.assertEqual(response.code, 415)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)
