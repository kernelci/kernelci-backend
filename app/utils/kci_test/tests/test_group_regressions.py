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

import logging
import mock
import mongomock
import random
import string
import unittest

import utils.kci_test.regressions as ktest_regressions


class TestGroupRegressions(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.db = mongomock.Database(mongomock.Connection(), "kernel-ci")

        self._id = "".join(
            [random.choice(string.digits) for x in xrange(24)])

        self.pass_test = {
            "name": "name",
            "job": "job",
            "kernel": "kernel",
            "arch": "arm64",
            "defconfig_full": "defconfig-full",
            "defconfig": "defconfig",
            "lab_name": "lab-foo",
            "board": "arm64-board",
            "created_on": "2018-11-29",
            "test_cases": [],
            "sub_groups": [],
        }

        self.fail_test = {
            "name": "name",
            "job": "job",
            "kernel": "kernel1",
            "arch": "arm64",
            "defconfig_full": "defconfig-full",
            "defconfig": "defconfig",
            "lab_name": "lab-foo",
            "board": "arm64-board",
            "created_on": "2018-11-30",
            "test_cases": [],
            "sub_groups": [],
        }

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_get_regressions_by_key_wrong_index(self):
        key = "a.b.c.d"
        regressions = {
            "a": {
                "b": {
                    "c": {
                        "d": {
                            "e": {
                                "f": ["foo"]
                            }
                        }
                    }
                }
            }
        }

        regr = ktest_regressions.get_regressions_by_key(key, regressions)
        self.assertListEqual([], regr)

    def test_get_regressions_by_key_wrong_key(self):
        key = "a.b.c.e.h.j"
        regressions = {
            "a": {
                "b": {
                    "c": {
                        "d": {
                            "e": {
                                "f": ["foo"]
                            }
                        }
                    }
                }
            }
        }

        regr = ktest_regressions.get_regressions_by_key(key, regressions)
        self.assertListEqual([], regr)

    def test_get_regressions_by_key(self):
        key = "a.b.c.d.e.f"
        regressions = {
            "a": {
                "b": {
                    "c": {
                        "d": {
                            "e": {
                                "f": ["foo"]
                            }
                        }
                    }
                }
            }
        }

        regr = ktest_regressions.get_regressions_by_key(key, regressions)
        self.assertListEqual(["foo"], regr)

    def test_generate_regression_keys(self):
        regressions = {
            "lab": {
                "arch": {
                    "board": {
                        "board_instance": {
                            "defconfig": {
                                "compiler": ["regression"]
                            }
                        }
                    }
                }
            }
        }
        expected = "lab.arch.board.board_instance.defconfig.compiler"

        for k in ktest_regressions.gen_regression_keys(regressions):
            self.assertEqual(expected, k)

    def test_sanitize_key(self):
        self.assertIsNone(None, ktest_regressions.sanitize_key(None))
        self.assertEqual("", ktest_regressions.sanitize_key(" "))

        key = "foo"
        self.assertEqual("foo", ktest_regressions.sanitize_key(key))

        key = "foo bar"
        self.assertEqual("foobar", ktest_regressions.sanitize_key(key))

        key = "foo.bar"
        self.assertEqual("foo:bar", ktest_regressions.sanitize_key(key))

        key = "foo bar.baz+foo"
        self.assertEqual("foobar:baz+foo", ktest_regressions.sanitize_key(key))

    @mock.patch("utils.db.find_one3")
    @mock.patch("utils.db.get_db_connection")
    def test_find_no_old_doc(self, mock_db, mock_find):
        mock_find.side_effects = [self.fail_test, None]

        results = ktest_regressions.find(self._id, {})
        self.assertTupleEqual((None, None), results)

    def test_create_regressions_key(self):
        expected = "lab-foo.arm64.arm64-board.none.defconfig-full.None"
        self.assertEqual(
            expected, ktest_regressions.create_regressions_key(self.pass_test))
