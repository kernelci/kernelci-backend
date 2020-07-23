# Copyright (C) Baylibre 2019
# Author: Khouloud Touil <ktouil@baylibre.com>
#
# Copyright (C) Collabora Limited 2018
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
#
# Copyright (C) Linaro Limited 2015,2017
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

"""Test module for the SendHandler."""

import datetime
import json
import mock
import tornado

import handlers.send as sendh

import urls

from handlers.tests.test_handler_base import TestHandlerBase


class TestSendHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application([urls._SEND_URL], **self.settings)

    def test_get(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/send", method="GET", headers=headers)

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_no_token(self):
        response = self.fetch("/send", method="GET")
        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/send", method="DELETE", headers=headers)

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete_no_token(self):
        response = self.fetch("/send", method="DELETE")
        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_no_token(self):
        response = self.fetch("/send", method="POST", body="")
        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_missing_job_key(self):
        headers = {
            "Authorization": "foo",
            "Content-Type": "application/json",
        }
        body = json.dumps(dict(kernel="kernel"))
        response = self.fetch(
            "/send", method="POST", headers=headers, body=body)
        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_missing_kernel_key(self):
        headers = {
            "Authorization": "foo",
            "Content-Type": "application/json",
        }
        body = json.dumps(dict(job="job"))
        response = self.fetch(
            "/send", method="POST", headers=headers, body=body)
        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_no_report_specified(self):
        headers = {
            "Authorization": "foo",
            "Content-Type": "application/json",
        }
        data = dict(job="job", kernel="kernel", delay=None)
        body = json.dumps(data)
        response = self.fetch(
            "/send", method="POST", headers=headers, body=body)
        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_wrong_delay(self):
        headers = {
            "Authorization": "foo",
            "Content-Type": "application/json",
        }
        data = dict(
            job="job",
            kernel="kernel",
            build_report=1, send_to="test@example.org", delay="foo"
        )
        body = json.dumps(data)
        response = self.fetch(
            "/send", method="POST", headers=headers, body=body)
        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("taskqueue.tasks.report.send_build_report")
    def test_post_build_report_correct(self, mock_schedule):
        mock_schedule.apply_async = mock.MagicMock()
        headers = {
            "Authorization": "foo",
            "Content-Type": "application/json",
        }
        data = dict(
            job="job",
            kernel="kernel",
            git_branch="master",
            build_report=1, send_to="test@example.org"
        )
        body = json.dumps(data)
        response = self.fetch(
            "/send", method="POST", headers=headers, body=body)
        self.assertEqual(response.code, 202)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)
        mock_schedule.apply_async.assert_called_with(
            [
                "job",
                "master",
                "kernel",
                {
                    "to": ["test@example.org"],
                    "cc": [],
                    "bcc": [],
                    "in_reply_to": None,
                    "subject": None,
                    "format": ["txt"],
                    "template": None,
                },
            ],
            countdown=60 * 60,
        )

    def test_post_build_report_no_email(self):
        headers = {
            "Authorization": "foo",
            "Content-Type": "application/json",
        }
        data = dict(
            job="job",
            kernel="kernel",
            build_report=1
        )
        body = json.dumps(data)
        response = self.fetch(
            "/send", method="POST", headers=headers, body=body)
        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_check_status(self):
        when = datetime.datetime.now()
        for report_type in ['build', 'test', 'bisect']:
            for errors in [True, False]:
                reason, status_code = sendh._check_status(
                    report_type, errors, when)
                self.assertIsNotNone(reason)
                self.assertEqual(status_code, 400 if errors else 202)

    def test_email_format(self):
        email_format, errors = sendh._check_email_format(None)

        self.assertListEqual(["txt"], email_format)
        self.assertEqual(0, len(errors))

        email_format, errors = sendh._check_email_format(["html"])

        self.assertListEqual(["html"], email_format)
        self.assertEqual(0, len(errors))

        email_format, errors = sendh._check_email_format(["txt"])

        self.assertListEqual(["txt"], email_format)
        self.assertEqual(0, len(errors))

        email_format, errors = sendh._check_email_format("foo")

        self.assertListEqual(["txt"], email_format)
        self.assertEqual(2, len(errors))

        email_format, errors = sendh._check_email_format(["foo"])

        self.assertListEqual(["txt"], email_format)
        self.assertEqual(2, len(errors))

        email_format, errors = sendh._check_email_format(["html", "txt"])

        self.assertListEqual(["html", "txt"], email_format)
        self.assertEqual(0, len(errors))
