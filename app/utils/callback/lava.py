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

TEST_CASE_MAP = {
    models.NAME_KEY: "name",
    models.STATUS_KEY: "result",
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


def _get_lava_job_meta(meta, boot_meta):
    """Parse the job meta-data from LAVA

    :param meta: The boot meta-data.
    :type meta: dictionary
    :param boot_meta: The boot and auto_login meta-data from the LAVA v2 job.
    :type boot_meta: dictionary
    """
    if boot_meta.get("error_type") == "Infrastructure":
        meta[models.BOOT_RESULT_KEY] = "UNKNOWN"


def _get_lava_boot_meta(meta, boot_meta):
    """Parse the boot and login meta-data from LAVA

    :param meta: The boot meta-data.
    :type meta: dictionary
    :param boot_meta: The boot and auto_login meta-data from the LAVA v2 job.
    :type boot_meta: dictionary
    """
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


def _get_lava_bootloader_meta(meta, bl_meta):
    """Parse the bootloader meta-data from LAVA

    :param meta: The boot meta-data.
    :type meta: dictionary
    :param bl_meta: The bootloader meta-data from the LAVA v2 job.
    :type bl_meta: dictionary
    """
    extra = bl_meta.get("extra", None)
    if extra is None:
        return
    for e in extra:
        for k, v in e.iteritems():
            meta_key = BL_META_MAP.get(k, None)
            if meta_key:
                meta[meta_key] = v


def _get_lava_meta(meta, job_data):
    """Parse the meta-data from LAVA

    Go through the LAVA meta-data and extract the fields needed to create a
    boot entry in the database.

    :param meta: The boot meta-data.
    :type meta: dictionary
    :param job_data: The JSON data from the callback.
    :type job_data: dict
    """
    lava = yaml.load(job_data["results"]["lava"], Loader=yaml.CLoader)
    meta_handlers = {
        'job': _get_lava_job_meta,
        'auto-login-action': _get_lava_boot_meta,
        'bootloader-overlay': _get_lava_bootloader_meta,
    }
    for step in lava:
        handler = meta_handlers.get(step["name"])
        if handler:
            handler(meta, step["metadata"])


def _get_directory_path(meta, base_path):
    """Create the dir_path from LAVA metadata

    Update the metadata with the storage path of the artifacts.
    If possible, use the file_server_resource from the metadata.

    :param meta: The boot meta-data.
    :type meta: dictionary
    :param base_path: The filesystem path where all storage is based
    :type base_path: dict
    """
    file_server_resource = meta.get(models.FILE_SERVER_RESOURCE_KEY)
    if file_server_resource:
        directory_path = os.path.join(
            base_path,
            file_server_resource,
            meta[models.LAB_NAME_KEY])
    else:
        directory_path = os.path.join(
            base_path,
            meta[models.JOB_KEY],
            meta[models.GIT_BRANCH_KEY],
            meta[models.KERNEL_KEY],
            meta[models.ARCHITECTURE_KEY],
            meta[models.DEFCONFIG_FULL_KEY],
            meta[models.BUILD_ENVIRONMENT_KEY],
            meta[models.LAB_NAME_KEY])
    meta[models.DIRECTORY_PATH] = directory_path


def add_log_fragments(groups, log, end_lines_map, start_log_line):
    lines_map = _prepare_lines_map(end_lines_map, start_log_line)
    for path, tc in _test_case_iter(groups):
        try:
            lines_range = lines_map[path]
            tc[models.LOG_LINES_KEY] = _get_log_lines(log, *lines_range)
        except KeyError:
            utils.LOG.warn(
                'No log lines specified for path: {} test_case {}'.format(
                    path, tc.get('name')))


def _test_case_iter(groups):
    for group in groups:
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


def _prepare_lines_map(end_lines_map, start_log_line):
    lines_map = OrderedDict(sorted(end_lines_map.items(),
                                   key=lambda i: i[1]))
    start_line = start_log_line
    for path, end_line in lines_map.items():
        lines_map[path] = (start_line, end_line)
        start_line = end_line + 1
    return lines_map


def _get_log_lines(log, start_line, end_line):
    lines = [
        {
            'dt': dparser.parse(line['dt']),
            'msg': line['msg']
        }
        for line in log[start_line:end_line]
    ]
    return lines


def _get_test_case(tests, names):
    tests_by_name = {t['name']: t for t in tests}
    for name in names:
        login = tests_by_name.get(name)
        if login:
            return login


def _add_login_case(meta, cases, login_tc):
    # ToDo: consolidate with _add_test_results
    test_case = {
        models.VERSION_KEY: "1.1",
        models.TIME_KEY: "0.0",
        models.NAME_KEY: "login",
        models.STATUS_KEY: login_tc["result"],
    }
    test_case.update({k: meta[k] for k in TEST_CASE_GROUP_KEYS})
    cases.append(test_case)


def _get_log_line_number(log, pattern):
    for line_number, line in enumerate(log):
        msg = line.get('msg', '')
        if pattern.match(unicode(msg)) is not None:
            return line_number


def _add_test_results(group, results, log_line_data):
    """Add test results from test suite data to a group.

    Import test results from a LAVA test suite into a group dictionary with the
    list of test cases that are not in any test set.  Test sets are converted
    into sub-groups with the test cases they contain.

    :param group: Test group data.
    :type group: dict
    :param results: Test results from the callback.
    :type results: dict
    :param log_line_data: dict of {test_case_path: log_end_line}
    :type log_line_data: dict
    """
    tests = results
    test_cases = []
    test_sets = OrderedDict()

    for test in reversed(tests):
        test_case = {
            models.VERSION_KEY: "1.1",
            models.TIME_KEY: "0.0",
        }
        path = [group.get('name')]
        test_case.update({k: test[v] for k, v in TEST_CASE_MAP.iteritems()})
        test_case.update({k: group[k] for k in TEST_CASE_GROUP_KEYS})
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
            path.append(test_set_name)
            test_case_list = test_sets.setdefault(test_set_name, [])
        else:
            test_case_list = test_cases
        path.append(test_case[models.NAME_KEY])
        log_line_data[tuple(path)] = int(test["log_end_line"])
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


def _adjust_log_line_numbers(results, log):
    """ A workaround for a race condition effect visible in LAVA callbacks

    This function changes log end line numbers in LAVA test results to match
    the moment when the signal was sent instead of when it was received.
    Function doesn't return value, but modifies results dictionary.
    """
    for ts, results_data in results.items():
        if ts == 'lava':
            continue
        for result in results_data:
            end_line_number = int(result['log_end_line'])
            log_end_line = log[end_line_number]
            test_case_rcvd = SIGNAL_RECEIVED_PATTERN.match(log_end_line['msg'])
            test_case_id = test_case_rcvd.group(1) if \
                test_case_rcvd is not None else None
            if test_case_id:
                result['log_end_line'] = _find_new_end_line(end_line_number,
                                                            log,
                                                            test_case_id)


def _find_new_end_line(end_line_number, log, test_case_id):
    signal_snd_template = r'<LAVA_SIGNAL_TESTCASE TEST_CASE_ID={}'
    signal_snd_text = signal_snd_template.format(test_case_id)
    signal_snd_pattern = re.compile(signal_snd_text)
    for i, log_line in enumerate(reversed(log[:end_line_number]), 1):
        if signal_snd_pattern.match(unicode(log_line['msg'])):
            return end_line_number - i
    return end_line_number


def _filter_log_data(log, filters_funcs):
    for filter_func in filters_funcs:
        log[:] = filter(filter_func, log)


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
        self._errors = {}
        self.base_path = base_path
        try:
            self.meta = self._prepare_meta(job_data, definition_meta, lab_name)
            self.results = self._prepare_results(job_data["results"])
            self.definition = yaml.load(job_data["definition"],
                                        Loader=yaml.CLoader)
            self.log = self._prepare_log(job_data["log"])
        except yaml.YAMLError:
            ret_code = 401
            msg = "Invalid test data from LAVA callback"
            utils.errors.add_error(self._errors, ret_code, msg)

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
        return meta

    def _prepare_results(self, results):
        return {test_suite: yaml.load(results_yaml, Loader=yaml.CLoader)
                for test_suite, results_yaml in results.items()}

    def _prepare_log(self, log):
        log = yaml.load(log, Loader=yaml.CLoader)
        for i, log_line in enumerate(log, 1):
            log_line['msg'] = unicode(log_line['msg'])
            log_line['org_num'] = i
            log_line['line_num'] = i
        return log

    def store_artifacts(self):
        try:
            self.store_test_log()
            self.store_lava_json()
            self.store_rootfs_info("build_info.json")
        except (OSError, IOError):
            ret_code = 500
            msg = "Internal error"
            utils.errors.add_error(self._errors, ret_code, msg)

    def store_lava_json(self):
        """ Save the json LAVA v2 callback object

        Save LAVA v2 callback data as json file.
        """

        file_name = "-".join(["lava-json", self.meta[models.DEVICE_TYPE_KEY]])
        file_name = ".".join([file_name, "json"])

        dir_path = self.meta[models.DIRECTORY_PATH]

        utils.LOG.info("Saving LAVA v2 callback file {} data in {}".format(
            file_name,
            dir_path))

        file_path = os.path.join(dir_path, file_name)

        # Removing the token
        self._job_data.pop("token", None)

        # Add extra information
        self._job_data["lab_name"] = self.meta.get("lab_name")
        self._job_data["version"] = self.meta.get("version")
        self._job_data["boot_log_html"] = self.meta.get("boot_log_html")

        if not os.path.isdir(dir_path):
            try:
                os.makedirs(dir_path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e

        with open(file_path, "wb") as f:
            f.write(json.dumps(self._job_data))

    def store_test_log(self):
        """Parse and save test logs

        Parse the LAVA v2 log in YAML format and save it
        as plain text and HTML.
        """

        dir_path = self.meta[models.DIRECTORY_PATH]
        suite = self.meta[models.PLAN_KEY]
        utils.LOG.info("Generating {} "
                       "log files in {}".format(suite, dir_path))
        file_name = "-".join([suite, self.meta[models.DEVICE_TYPE_KEY]])
        files = tuple(".".join([file_name, ext]) for ext in ["txt", "html"])
        (self.meta[models.BOOT_LOG_KEY],
         self.meta[models.BOOT_LOG_HTML_KEY]) = files
        txt_path, html_path = (os.path.join(dir_path, f) for f in files)

        if not os.path.isdir(dir_path):
            try:
                os.makedirs(dir_path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e

        with codecs.open(txt_path, "w", "utf-8") as txt:
            with codecs.open(html_path, "w", "utf-8") as html:
                utils.lava_log_parser.run(self.log, self.meta, txt, html)

    def store_rootfs_info(self, file_name):
        """Add rootfs info

        Parse the the JSON file with the information of the rootfs if it's
        available and add its information to the group data.  If the file URL
        matches the local storage server, then read it directly from the file
        system.
        """

        rootfs_url = self.meta.get("initrd")
        if not rootfs_url or rootfs_url == "None":
            return

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
            self.meta[models.INITRD_INFO_KEY] = rootfs_info
        except IOError as e:
            utils.LOG.warn("IOError: {}".format(e))
        except ValueError as e:
            utils.LOG.warn("ValueError: {}".format(e))


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
    plan = None
    plan_doc_id = None
    errors = {}
    ex = None
    msg = None

    utils.LOG.info("Processing LAVA test data: job {} from {}".format(
        job_data["id"], lab_name))

    if job_data.get("status") not in (COMPLETE, INCOMPLETE):
        utils.LOG.warning("Skipping LAVA job due to unsupported status: "
                          "{}".format(job_data["status_string"]))
        return None

    meta = {
        models.VERSION_KEY: "1.1",
        models.LAB_NAME_KEY: lab_name,
        models.TIME_KEY: "0.0",
    }

    try:
        callback = LavaCallback.process_callback(job_data, job_meta,
                                                 lab_name, base_path)
        groups = []
        cases = []
        start_log_line = 0
        end_lines_map = {}
        job_tc = None
        login_tc = None
        for suite_name, suite_results in callback.results.iteritems():
            if suite_name == "lava":
                login_tc = _get_test_case(suite_results,
                                          ('login-action',
                                           'auto-login-action'))
                job_tc = _get_test_case(suite_results, ('job',))
                login_line_num = _get_log_line_number(callback.log,
                                                      LOGIN_CASE_END_PATTERN)
                start_log_line = 0 if login_line_num is None \
                    else login_line_num
            else:
                suite_name = suite_name.partition("_")[2]
                group = dict(meta)
                group[models.NAME_KEY] = suite_name
                _add_test_results(group, suite_results,
                                  end_lines_map)
                groups.append(group)
        if login_tc and login_tc.get('result') == 'pass' and len(groups) == 0:
            login_tc = job_tc
        if login_tc:
            _add_login_case(meta, cases, login_tc)
        add_log_fragments(groups, callback.log, end_lines_map, start_log_line)

        plan_name = callback.meta[models.PLAN_KEY]
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
            plan = dict(meta)
            plan[models.NAME_KEY] = plan_name
            plan[models.SUB_GROUPS_KEY] = groups
            plan[models.TEST_CASES_KEY] = cases

        if plan:
            ret_code, plan_doc_id, err = \
                utils.kci_test.import_and_save_kci_tests(plan, db_options)
            utils.errors.update_errors(errors, err)
    finally:
        if ex is not None:
            utils.LOG.exception(ex)
        if msg is not None:
            utils.LOG.error(msg)
            utils.errors.add_error(errors, ret_code, msg)
        if errors:
            raise utils.errors.BackendError(errors)

    if not plan_doc_id:
        utils.LOG.warn("No test results")
        return None

    return plan_doc_id
