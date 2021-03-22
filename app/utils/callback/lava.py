# Copyright (C) Baylibre -0700,2017,2018,2019
# Author: Kevin Hilman <khilman@baylibre.com>
# Author: Khouloud Touil <ktouil@baylibre.com>
# Author: Loys Ollivier <lollivier@baylibre.com>
# Author: lollivier <lollivier@baylibre.com>
#
# Copyright (C) Collabora Limited 2017,2018,2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Michal Galka <michal.galka@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
#
# Copyright (C) Linaro Limited 2018,2019
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

import codecs
import dateutil.parser as dparser
import errno
import models
import os
import re
import yaml
import json
import urllib2
from collections import OrderedDict
from urlparse import urlparse


import utils
import utils.kci_test
import utils.db
import utils.lava_log_parser
from utils.report.common import DEFAULT_STORAGE_URL
from utils.callback.lava_filters import LAVA_FILTERS

# copied from lava-server/lava_scheduler_app/models.py
SUBMITTED = 0
RUNNING = 1
COMPLETE = 2
INCOMPLETE = 3
CANCELED = 4
CANCELING = 5

LAVA_JOB_RESULT = {
    COMPLETE: "PASS",
    INCOMPLETE: "FAIL",
    CANCELED: "UNKNOWN",
    CANCELING: "UNKNOWN",
}

TEST_CASE_NAME_EXTRA = {
    "http-download": ["label"],
    "git-repo-action": ["commit", "path"],
    "test-overlay": ["name"],
    "test-runscript-overlay": ["name"],
    "test-install-overlay": ["name"],
}

BL_META_MAP = {
    "ramdisk_addr": "initrd_addr",
    "kernel_addr": "loadaddr",
    "dtb_addr": "dtb_addr",
}

LOGIN_CASE_END_PATTERN = re.compile(r'end:.*auto-login-action.*')
TEST_CASE_SIGNAL_PATTERN = re.compile(
    r'\<LAVA_SIGNAL_TESTCASE TEST_CASE_ID.+>')
SIGNAL_RECEIVED_PATTERN = re.compile(r'Received signal: '
                                     r'<TESTCASE> TEST_CASE_ID=(\w+)')


def _get_job_meta(meta, job_data):
    """Parse the main job meta-data from LAVA

    :param meta: The meta-data to populate.
    :type meta: dictionary
    :param job_data: The JSON data from the callback.
    :type job_data: dict
    :param job_data: The map of keys to search for in the JSON and update.
    :type job_data: dict
    """
    meta[models.BOOT_RESULT_KEY] = LAVA_JOB_RESULT[job_data["status"]]
    meta[models.BOARD_INSTANCE_KEY] = job_data["actual_device_id"]


def _get_definition_meta(meta, job_meta, meta_data_map):
    """Parse the job definition meta-data from LAVA

    Parse the meta-data from the LAVA v2 job definition sent with the callback
    and populate the required fields to store in the database.

    :param meta: The meta-data to populate.
    :type meta: dictionary
    :param job_data: The JSON data from the callback.
    :type job_data: dict
    :param job_data: The map of keys to search for in the JSON and update.
    :type job_data: dict
    :param meta_data_map: The dict of keys to parse and add in the meta-data.
    :type meta_data_map: dict
    """
    for x, y in meta_data_map.iteritems():
        try:
            meta.update({x: job_meta[y]})
        except (KeyError) as ex:
            utils.LOG.warn("Metadata field {} missing in the job"
                           " result.".format(ex))


def _get_test_case(tests, names):
    tests_by_name = {t['name']: t for t in tests}
    for name in names:
        login = tests_by_name.get(name)
        if login:
            return login


def _prepare_line_num_translate(results_data, log):
    end_line_numbers = []
    for test_suite, results_data in results_data.items():
        end_line_numbers.extend((int(result['log_end_line'])
                                 for result in results_data
                                 if result.get('log_end_line')))
    line_num_translate = dict.fromkeys(end_line_numbers)
    for idx, log_line in enumerate(log, 1):
        for line_num in (ln for ln in line_num_translate
                         if line_num_translate[ln] is None):
            if log_line['org_num'] >= line_num:
                line_num_translate[line_num] = idx
    return line_num_translate


def _translate_log_end_lines(results, translate_map):
    for ts, results_data in results.items():
        if ts == 'lava':
            continue
        for result in results_data:
            new_log_end_line = translate_map.get(int(result['log_end_line']))
            if new_log_end_line:
                result['log_end_line'] = new_log_end_line


class LavaCallback(object):
    META_DATA_MAP_TEST = {
        models.ARCHITECTURE_KEY: "job.arch",
        models.DEFCONFIG_KEY: "kernel.defconfig",
        models.DEFCONFIG_FULL_KEY: "kernel.defconfig_full",
        models.DEVICE_TYPE_KEY: "device.type",
        models.DTB_KEY: "platform.dtb",
        models.ENDIANNESS_KEY: "kernel.endian",
        models.GIT_BRANCH_KEY: "git.branch",
        models.GIT_COMMIT_KEY: "git.commit",
        models.GIT_DESCRIBE_KEY: "git.describe",
        models.GIT_URL_KEY: "git.url",
        models.INITRD_KEY: "job.initrd_url",
        models.JOB_KEY: "kernel.tree",
        models.KERNEL_KEY: "kernel.version",
        models.KERNEL_IMAGE_KEY: "job.kernel_image",
        models.MACH_KEY: "platform.mach",
        models.PLAN_KEY: "test.plan",
        models.PLAN_VARIANT_KEY: "test.plan_variant",
        models.BUILD_ENVIRONMENT_KEY: "job.build_environment",
        models.FILE_SERVER_RESOURCE_KEY: "job.file_server_resource",
    }

    @classmethod
    def process_callback(cls, job_data, definition_meta, lab_name,
                         base_path=utils.BASE_PATH):
        utils.LOG.info("Processing LAVA test data: job {} from {}".format(
            job_data["id"], lab_name))

        if job_data.get("status") not in (COMPLETE, INCOMPLETE):
            utils.LOG.warning("Skipping LAVA job due to unsupported status: "
                              "{}".format(job_data["status_string"]))
            return None
        return cls(job_data, definition_meta, lab_name, base_path)

    def __init__(self, job_data, definition_meta, lab_name,
                 base_path):
        self._job_data = job_data
        self.base_path = base_path
        self.results = self._prepare_results(job_data["results"])
        self.meta = self._prepare_meta(job_data, definition_meta, lab_name)
        self.definition = yaml.load(job_data["definition"],
                                    Loader=yaml.CLoader)
        self.log = self._prepare_log(job_data["log"])

    def _get_lava_job_meta(self, boot_meta):
        """Parse the job meta-data from LAVA

        :param meta: The boot meta-data.
        :type meta: dictionary
        :param boot_meta: The boot and auto_login meta-data
               from the LAVA v2 job.
        :type boot_meta: dictionary
        """
        meta = {}
        if boot_meta.get("error_type") == "Infrastructure":
            meta[models.BOOT_RESULT_KEY] = "UNKNOWN"
        return meta

    def _get_lava_boot_meta(self, boot_meta):
        """Parse the boot and login meta-data from LAVA

        :param boot_meta: The boot and auto_login meta-data
               from the LAVA v2 job.
        :type boot_meta: dictionary
        :return meta: The boot meta-data dict
        """
        meta = {}
        meta[models.BOOT_TIME_KEY] = boot_meta["duration"]
        extra = boot_meta.get("extra", None)
        if extra is None:
            return
        kernel_messages = []
        for e in extra:
            fail = e.get("fail", None)
            if not fail:
                continue
            if isinstance(fail, str):
                kernel_messages.append(fail)
            else:
                for msg in (f.get("message", None) for f in fail):
                    if msg:
                        kernel_messages.append(msg)
        if kernel_messages:
            meta[models.BOOT_WARNINGS_KEY] = len(kernel_messages)
        return meta

    def _get_lava_bootloader_meta(self, bl_meta):
        """Parse the bootloader meta-data from LAVA

        :param bl_meta: The bootloader meta-data from the LAVA v2 job.
        :type bl_meta: dictionary
        :return The boot meta-data
        """
        meta = {}
        extra = bl_meta.get("extra", None)
        if extra is None:
            return
        for e in extra:
            for k, v in e.iteritems():
                meta_key = BL_META_MAP.get(k, None)
                if meta_key:
                    meta[meta_key] = v
        return meta

    def _get_directory_path(self, meta):
        """Create the dir_path from LAVA metadata

        Update the metadata with the storage path of the artifacts.
        If possible, use the file_server_resource from the metadata.

        :param meta: The boot meta-data.
        :type meta: dictionary
        """

        file_server_resource = meta.get(models.FILE_SERVER_RESOURCE_KEY)
        if file_server_resource:
            directory_path = os.path.join(
                self.base_path,
                file_server_resource,
                meta[models.LAB_NAME_KEY])
        else:
            directory_path = os.path.join(
                self.base_path,
                meta[models.JOB_KEY],
                meta[models.GIT_BRANCH_KEY],
                meta[models.KERNEL_KEY],
                meta[models.ARCHITECTURE_KEY],
                meta[models.DEFCONFIG_FULL_KEY],
                meta[models.BUILD_ENVIRONMENT_KEY],
                meta[models.LAB_NAME_KEY])
        return directory_path

    def _get_lava_meta(self):
        """Parse the meta-data from LAVA

        Go through the LAVA meta-data and extract the fields needed to create a
        boot entry in the database.

        :return LAVA metadata dict
        """
        lava = self.results["lava"]
        meta_handlers = {
            'job': self._get_lava_job_meta,
            'auto-login-action': self._get_lava_boot_meta,
            'login-action': self._get_lava_boot_meta,
            'bootloader-overlay': self._get_lava_bootloader_meta,
        }
        meta = {}
        for step in lava:
            handler = meta_handlers.get(step["name"])
            if handler:
                meta.update(handler(step["metadata"]))
        return meta

    def _prepare_meta(self, job_data, definition_meta, lab_name):
        meta = {
            models.VERSION_KEY: "1.1",
            models.LAB_NAME_KEY: lab_name,
            models.TIME_KEY: "0.0",
            models.BOOT_RESULT_KEY: LAVA_JOB_RESULT[job_data["status"]],
            models.BOARD_INSTANCE_KEY: job_data["actual_device_id"]
        }

        for x, y in self.META_DATA_MAP_TEST.iteritems():
            try:
                meta.update({x: definition_meta[y]})
            except KeyError as ex:
                utils.LOG.warn("Metadata field {} missing in the job"
                               " result.".format(ex))
        meta.update(self._get_lava_meta())
        meta[models.DIRECTORY_PATH] = self._get_directory_path(meta)
        rootfs_url = meta.get(models.INITRD_KEY)
        if rootfs_url and rootfs_url != "None":
            rootfs_info = self._get_rootfs_info(rootfs_url)
            if rootfs_info:
                meta[models.INITRD_INFO_KEY] = rootfs_info
        return meta

    def _prepare_results(self, results):
        return {test_suite: yaml.load(results_yaml, Loader=yaml.CLoader)
                for test_suite, results_yaml in results.items()}

    def _prepare_log(self, log):
        log = yaml.load(log, Loader=yaml.CLoader)
        for i, log_line in enumerate(log, 1):
            log_line['msg'] = unicode(log_line['msg'])
        return log

    def _get_rootfs_info(self, rootfs_url, file_name='build_info.json'):
        """Add rootfs info

        Parse the the JSON file with the information of the rootfs if it's
        available and add its information to the group data.  If the file URL
        matches the local storage server, then read it directly from the file
        system.
        """
        rootfs_info = None
        try:
            # compare to default URL without the scheme
            _default_url = urlparse(DEFAULT_STORAGE_URL).netloc
            _rootfs_url = urlparse(rootfs_url).netloc
            if _rootfs_url.startswith(_default_url):
                rootfs_url_path = urlparse(rootfs_url).path
                rootfs_rel_dir = os.path.dirname(rootfs_url_path).lstrip("/")
                json_file = os.path.join(self.base_path, rootfs_rel_dir,
                                         file_name)
                rootfs_info_json = open(json_file)
            else:
                rootfs_top_url = rootfs_url.rpartition("/")[0]
                file_url = "/".join([rootfs_top_url, file_name])
                utils.LOG.info("Downloading rootfs info: {}".format(file_url))
                rootfs_info_json = urllib2.urlopen(file_url)
            rootfs_info = json.load(rootfs_info_json)
        except IOError as e:
            utils.LOG.warn("IOError: {}".format(e))
        except ValueError as e:
            utils.LOG.warn("ValueError: {}".format(e))
        return rootfs_info


def store_artifacts(metadata, job_data, log):
    store_test_log(metadata, log)
    store_lava_json(metadata, job_data)


def store_lava_json(metadata, job_data):
    """ Save the json LAVA v2 callback object

    Save LAVA v2 callback data as json file.
    """

    file_name = "-".join(["lava-json", metadata[models.DEVICE_TYPE_KEY]])
    file_name = ".".join([file_name, "json"])

    dir_path = metadata[models.DIRECTORY_PATH]

    utils.LOG.info("Saving LAVA v2 callback file {} data in {}".format(
        file_name,
        dir_path))

    file_path = os.path.join(dir_path, file_name)

    # Removing the token
    job_data.pop("token", None)

    # Add extra information
    job_data["lab_name"] = metadata.get("lab_name")
    job_data["version"] = metadata.get("version")
    job_data["boot_log_html"] = metadata.get("boot_log_html")
    utils.make_path(dir_path)
    with open(file_path, "wb") as f:
        f.write(json.dumps(job_data))


def store_test_log(metadata, log):
    """Parse and save test logs

    Parse the LAVA v2 log in YAML format and save it
    as plain text and HTML.
    """

    dir_path = metadata[models.DIRECTORY_PATH]
    suite = metadata[models.PLAN_KEY]
    utils.LOG.info("Generating {} "
                   "log files in {}".format(suite, dir_path))
    file_name = "-".join([suite, metadata[models.DEVICE_TYPE_KEY]])
    files = tuple(".".join([file_name, ext]) for ext in ["txt", "html"])
    (metadata[models.BOOT_LOG_KEY],
     metadata[models.BOOT_LOG_HTML_KEY]) = files
    txt_path, html_path = (os.path.join(dir_path, f) for f in files)
    utils.make_path(dir_path)
    with codecs.open(txt_path, "w", "utf-8") as txt:
        with codecs.open(html_path, "w", "utf-8") as html:
            utils.lava_log_parser.run(log, metadata, txt, html)


class LogFragmentsMixin(object):
    LOGIN_CASE_END_PATTERN = re.compile(r'end:.*login-action.*')
    TEST_CASE_SIGNAL_PATTERN = re.compile(
        r'\<LAVA_SIGNAL_TESTCASE TEST_CASE_ID.+>')
    SIGNAL_RECEIVED_PATTERN = re.compile(r'Received signal: '
                                         r'<TESTCASE> TEST_CASE_ID=(\w+)')

    def _add_log_fragments(self):
        lines_map = []
        for path, tc in self._test_case_iter():
            tc = tc
            log_end_line = tc.get('log_end_line')
            if log_end_line:
                new_end_line = self._adjust_log_end_line(int(log_end_line))
                lines_map.append((tc, int(new_end_line)))
            else:
                utils.LOG.warn('Log end line number not found for {}'
                               .format('.'.join(path)))
        start_line = self.start_log_line
        for tc, end_line in sorted(lines_map, key=lambda x: x[1]):
            tc[models.LOG_LINES_KEY] = self.log[start_line: end_line]
            start_line = end_line + 1 \
                if end_line < len(self.log) else end_line

    @property
    def start_log_line(self):
        line_number = self._get_log_line_number(self.LOGIN_CASE_END_PATTERN)
        return 0 if line_number is None else line_number

    def _get_log_line_number(self, pattern):
        for line_number, line in enumerate(self.log):
            msg = line.get('msg', '')
            if pattern.match(unicode(msg)) is not None:
                return line_number

    def _find_new_end_line(self, end_line_number, test_case_id):
        signal_snd_template = r'<LAVA_SIGNAL_TESTCASE TEST_CASE_ID={}'
        signal_snd_text = signal_snd_template.format(test_case_id)
        signal_snd_pattern = re.compile(signal_snd_text)
        for i, log_line in enumerate(reversed(self.log[:end_line_number]), 1):
            if signal_snd_pattern.match(unicode(log_line['msg'])):
                return end_line_number - i
        return end_line_number

    def _adjust_log_end_line(self, end_line_number):
        log_end_line = self.log[end_line_number]
        test_case_rcvd = \
            self.SIGNAL_RECEIVED_PATTERN.match(log_end_line['msg'])
        test_case_id = test_case_rcvd.group(1) if \
            test_case_rcvd is not None else None
        if test_case_id:
            return self._find_new_end_line(end_line_number, test_case_id)
        return end_line_number

    @staticmethod
    def _prepare_lines_map(end_lines_map, start_log_line):
        lines_map = OrderedDict(sorted(end_lines_map.items(),
                                       key=lambda i: i[1]))
        start_line = start_log_line
        for path, end_line in lines_map.items():
            lines_map[path] = (start_line, end_line)
            start_line = end_line + 1
        return lines_map

    def _test_case_iter(self):
        for group in self.groups:
            stack = [group]
            path = [group.get('name')]
            while stack:
                node = stack.pop()
                if node is not group:
                    path.append(node.get('name'))
                for test_case in node.get('test_cases', []):
                    path.append(test_case.get('name'))
                    yield tuple(path), test_case
                    path.pop()
                if node is not group:
                    path.pop()
                for sub_group in node.get('sub_groups', []):
                    stack.append(sub_group)

    def _get_log_lines(self, start_line, end_line):
        lines = [
            {
                'dt': dparser.parse(line['dt']),
                'msg': line['msg'],
                'lvl': line['lvl']
            }
            for line in self.log[start_line:end_line]
        ]
        return lines

    @staticmethod
    def _filter_log_data(log, filters_funcs):
        for filter_func in filters_funcs:
            log[:] = filter(filter_func, log)


class LavaPlan(object):
    def __init__(self, groups, cases, metadata):
        self.data = self._create_plan(groups, cases, metadata)

    def _create_plan(self, groups, cases, metadata):
        plan_name = metadata[models.PLAN_KEY]
        plan = None
        if ((len(groups) == 1) and
                (groups[0][models.NAME_KEY] == plan_name)):
            # Only one group with same name as test plan
            plan = groups[0]
            if cases:
                insert_len = len(cases)
                plan_cases = plan[models.TEST_CASES_KEY]
                cases.extend(plan_cases)
                plan[models.TEST_CASES_KEY] = cases
        elif groups or cases:
            # Create top-level group with the test plan name
            plan = dict(metadata)
            plan[models.NAME_KEY] = plan_name
            plan[models.SUB_GROUPS_KEY] = groups
            plan[models.TEST_CASES_KEY] = cases
        return plan


class LavaResults(LogFragmentsMixin):
    TEST_CASE_MAP = {
        models.NAME_KEY: "name",
        models.STATUS_KEY: "result",
        "log_end_line": "log_end_line"
    }

    TEST_CASE_GROUP_KEYS = [
        models.ARCHITECTURE_KEY,
        models.BUILD_ENVIRONMENT_KEY,
        models.DEFCONFIG_FULL_KEY,
        models.DEVICE_TYPE_KEY,
        models.GIT_BRANCH_KEY,
        models.GIT_COMMIT_KEY,
        models.JOB_KEY,
        models.KERNEL_KEY,
        models.LAB_NAME_KEY,
        models.MACH_KEY,
    ]

    def __init__(self, results, metadata, log):
        self.groups, self.cases = self._populate_results(results,
                                                         metadata)
        self.log = log
        self._add_log_fragments()
        self._filter_log_lines()

    def _get_test_case(self, tests, names):
        tests_by_name = {t['name']: t for t in tests}
        for name in names:
            login = tests_by_name.get(name)
            if login:
                return login

    def _populate_results(self, results, metadata):
        groups = []
        cases = []
        job_tc = None
        login_tc = None
        for suite_name, suite_results in results.iteritems():
            if suite_name == "lava":
                login_tc = self._get_test_case(suite_results,
                                               ('login-action',
                                                'auto-login-action'))
                job_tc = self._get_test_case(suite_results, ('job',))
            else:
                suite_name = suite_name.partition("_")[2]
                group = dict(metadata)
                group[models.NAME_KEY] = suite_name
                self._add_test_results(group, suite_results)
                groups.append(group)
        if login_tc and login_tc.get('result') == 'pass' and len(groups) == 0:
            login_tc = job_tc
        if login_tc:
            cases.append(self._create_login_case(metadata, login_tc))
        return groups, cases

    def _filter_log_lines(self):
        for _, tc in self._test_case_iter():
            log_lines = tc.get(models.LOG_LINES_KEY)
            if log_lines:
                self._filter_log_data(log_lines, LAVA_FILTERS)

    def _create_login_case(self, meta, login_tc):
        # ToDo: consolidate with _add_test_results
        test_case = {
            models.VERSION_KEY: "1.1",
            models.TIME_KEY: "0.0",
            models.NAME_KEY: "login",
            models.STATUS_KEY: login_tc["result"],
        }
        test_case.update({k: meta[k] for k in self.TEST_CASE_GROUP_KEYS})
        return test_case

    def _add_test_results(self, group, results):
        """Add test results from test suite data to a group.

        Import test results from a LAVA test suite into a group dictionary
        with the list of test cases that are not in any test set.
        Test sets are converted into sub-groups with the test cases they
        contain.

        :param group: Test group data.
        :type group: dict
        :param results: Test results from the callback.
        :type results: dict
        """
        tests = results
        test_cases = []
        test_sets = OrderedDict()

        for test in reversed(tests):
            test_case = {
                models.VERSION_KEY: "1.1",
                models.TIME_KEY: "0.0",
            }
            test_case.update({k: test[v]
                              for k, v in self.TEST_CASE_MAP.iteritems()})
            test_case.update({k: group[k]
                              for k in self.TEST_CASE_GROUP_KEYS})
            measurement = test.get("measurement")
            if measurement and measurement != 'None':
                test_case[models.MEASUREMENTS_KEY] = [{
                    "value": float(measurement),
                    "unit": test["unit"],
                }]
            test_meta = test["metadata"]
            reference = test_meta.get("reference")
            if reference:
                test_case[models.ATTACHMENTS_KEY] = [reference]
            test_set_name = test_meta.get("set")
            if test_set_name:
                test_case_list = test_sets.setdefault(test_set_name, [])
            else:
                test_case_list = test_cases
            test_case_list.append(test_case)

        sub_groups = []
        for test_set in test_sets.iteritems():
            test_set_name, test_set_cases = test_set
            sub_group = {
                models.NAME_KEY: test_set_name,
                models.TEST_CASES_KEY: test_set_cases,
            }
            sub_groups.append(sub_group)

        group.update({
            models.TEST_CASES_KEY: test_cases,
            models.SUB_GROUPS_KEY: sub_groups,
        })


def add_tests(job_data, job_meta, lab_name, db_options,
              base_path=utils.BASE_PATH):
    """Entry point to be used as an external task.

    This function should only be called by Celery or other task managers.
    Parse the test data from a LAVA v2 job callback and save it along with
    kernel logs.

    :param job_data: The JSON data from the callback.
    :type job_data: dict
    :param lab_name: Name of the LAVA lab that posted the callback.
    :type lab_name: string
    :param db_options: The mongodb database connection parameters.
    :type db_options: dict
    :param base_path: Path to the top-level directory where to save files.
    :type base_path: string
    :return The top-level test group document id as ObjectId object.
    """
    ret_code = 201
    plan_doc_id = None
    errors = {}

    callback = None
    try:
        callback = LavaCallback.process_callback(job_data, job_meta,
                                                 lab_name, base_path)
    except yaml.YAMLError as ex:
        ret_code = 401
        msg = "Invalid test data from LAVA callback"
        utils.errors.add_error(errors, ret_code, msg)
        handle_errors(ex, msg, errors)

    if callback is None:
        return None

    try:
        store_artifacts(callback.meta, job_data, callback.log)
    except (OSError, IOError) as ex:
        ret_code = 500
        msg = "Internal error"
        utils.errors.add_error(errors, ret_code, msg)
        handle_errors(ex, msg, errors)

    test_results = LavaResults(callback.results,
                               callback.meta,
                               callback.log)
    plan = LavaPlan(test_results.groups, test_results.cases, callback.meta)

    if plan.data:
        ret_code, plan_doc_id, err = \
            utils.kci_test.import_and_save_kci_tests(plan.data, db_options)
        utils.errors.update_errors(errors, err)
        handle_errors(errors=errors)

    if not plan_doc_id:
        utils.LOG.warn("No test results")
        return None

    return plan_doc_id


def handle_errors(ex=None, msg=None, errors=None):
    if ex is not None:
        utils.LOG.exception(ex)
    if msg is not None:
        utils.LOG.error(msg)
    if errors:
        raise utils.errors.BackendError(errors)
