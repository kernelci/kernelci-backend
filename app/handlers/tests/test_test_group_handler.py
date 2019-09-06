# Copyright (C) 2014 Linaro Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Test module for the TestGroupHandler handler."""

import bson
import json
import mock
import tornado
import unittest

import urls

from handlers.tests.test_handler_base import TestHandlerBase


class TestTestGroupHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application([urls._TEST_GROUP_URL], **self.settings)

    @mock.patch("utils.db.find_and_count")
    def test_get(self, mock_find):
        mock_find.return_value = ([{"foo": "bar"}], 1)

        headers = {"Authorization": "foo"}
        response = self.fetch("/test/group/", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("bson.objectid.ObjectId")
    @mock.patch("handlers.test_group.TestGroupHandler.collection")
    def test_get_by_id_not_found(self, collection, mock_id):
        mock_id.return_value = "suite-id"
        collection.find_one = mock.MagicMock()
        collection.find_one.return_value = None

        headers = {"Authorization": "foo"}
        response = self.fetch("/test/group/suite-id", headers=headers)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("bson.objectid.ObjectId")
    @mock.patch("handlers.test_group.TestGroupHandler.collection")
    def test_get_by_id_not_found_empty_list(self, collection, mock_id):
        mock_id.return_value = "suite-id"
        collection.find_one = mock.MagicMock()
        collection.find_one.return_value = []

        headers = {"Authorization": "foo"}
        response = self.fetch("/test/group/suite-id", headers=headers)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("bson.objectid.ObjectId")
    @mock.patch("handlers.test_group.TestGroupHandler.collection")
    def test_get_by_id_found(self, collection, mock_id):
        mock_id.return_value = "suite-id"
        collection.find_one = mock.MagicMock()
        collection.find_one.return_value = {"_id": "suite-id"}

        headers = {"Authorization": "foo"}
        response = self.fetch("/test/group/suite-id", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_without_token(self):
        body = json.dumps(dict(name="suite", version="1.0"))

        response = self.fetch("/test/group", method="POST", body=body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_not_json_content(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/test/group", method="POST", body="", headers=headers)

        self.assertEqual(response.code, 422)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_wrong_content_type(self):
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/test/group", method="POST", body="", headers=headers)

        self.assertEqual(response.code, 415)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_wrong_json(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        body = json.dumps(dict(foo="foo", bar="bar"))

        response = self.fetch(
            "/test/group", method="POST", body=body, headers=headers)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("utils.db.get_db_connection")
    @mock.patch("utils.db.save")
    def test_post_correct(self, mock_save, mock_db):
        mock_save.return_value = (201, "test-suite-id")
        mock_db.return_value = self.database
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        body = json.dumps(
            dict(
                name="test",
                lab_name="lab_name", version="1.0", build_id="build",
                build_environment="build-environment",
                board="board",
                defconfig="defconfig",
                job="job",
                kernel="kernel",
                git_commit="git_commit",
                time=1.0,
                test_cases=[],
                arch="x86",
                git_branch="branch"
                )
        )

        response = self.fetch(
            "/test/group", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 201)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_correct_with_id(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(
            dict(
                name="suite",
                version="1.0", lab_name="lab", build_id="build")
        )

        response = self.fetch(
            "/test/group/fake-id", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("utils.db.get_db_connection")
    def test_post_correct_with_test_cases(self,
                                          mock_db):
        mock_db.return_value = self.database
        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(
            dict(
                name="suite",
                version="1.0",
                lab_name="lab",
                build_id="build", test_cases=[{"name": "foo",
                                               "status": "pass",
                                               "time": 1.0}],
                build_environment="build_environment",
                board="board",
                defconfig="defconfig",
                job="job",
                kernel="kernel",
                git_commit="git_commit",
                time=1.0,
                arch="x86",
                git_branch="branch"
            )
        )

        response = self.fetch(
            "/test/group", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 201)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("utils.db.get_db_connection")
    @mock.patch("utils.db.save")
    def test_post_correct_with_error(self, mock_save, mock_db):
        mock_save.return_value = (500, None)
        mock_db.return_value = self.database
        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(
            dict(
                name="test", lab_name="lab_name", version="1.0",
                build_environment="build-environment",
                arch="x86", defconfig="defconfig", git_branch="git_branch",
                job="job", kernel="kernel")
        )

        response = self.fetch(
            "/test/group", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 500)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)
