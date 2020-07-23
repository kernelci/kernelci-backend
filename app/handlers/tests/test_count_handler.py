# Copyright (C) Linaro Limited 2014,2015
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

"""Test module for the CountHandler handler."""

import json
import tornado

import urls

from handlers.tests.test_handler_base import TestHandlerBase


class TestCountHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application([urls._COUNT_URL], **self.settings)

    def test_post(self):
        body = json.dumps(dict(job="job", kernel="kernel"))

        response = self.fetch("/count", method="POST", body=body)

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete(self):
        response = self.fetch("/count", method="DELETE")

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_wrong_resource(self):
        headers = {"Authorization": "foo"}

        response = self.fetch("/count/foobar", headers=headers)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_count_all(self):
        headers = {"Authorization": "foo"}
        response = self.fetch("/count", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_count_all_with_query(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/count?board=foo&status=FAIL", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_count_collection(self):
        headers = {"Authorization": "foo"}
        response = self.fetch("/count/build", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_count_collection_with_query(self):
        headers = {"Authorization": "foo"}
        response = self.fetch("/count/build?arch=foo", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)
