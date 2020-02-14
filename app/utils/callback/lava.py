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

import utils
import utils.boot
import utils.kci_test
import utils.db
import utils.lava_log_parser
from utils.report.common import DEFAULT_STORAGE_URL

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

META_DATA_MAP_TEST = {
    models.ARCHITECTURE_KEY: "job.arch",
    models.BOARD_KEY: "platform.name",
    models.DEFCONFIG_KEY: "kernel.defconfig_base",
    models.DEFCONFIG_FULL_KEY: "kernel.defconfig",
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
    models.IMAGE_TYPE_KEY: "image.type",
    models.PLAN_KEY: "test.plan",
    models.PLAN_VARIANT_KEY: "test.plan_variant",
    models.BUILD_ENVIRONMENT_KEY: "job.build_environment",
    models.FILE_SERVER_RESOURCE_KEY: "job.file_server_resource",
}

META_DATA_MAP_BOOT = {
    models.DEFCONFIG_KEY: "kernel.defconfig_base",
    models.DEFCONFIG_FULL_KEY: "kernel.defconfig",
    models.GIT_BRANCH_KEY: "git.branch",
    models.GIT_COMMIT_KEY: "git.commit",
    models.GIT_DESCRIBE_KEY: "git.describe",
    models.GIT_URL_KEY: "git.url",
    models.KERNEL_KEY: "kernel.version",
    models.KERNEL_IMAGE_KEY: "job.kernel_image",
    models.ENDIANNESS_KEY: "kernel.endian",
    models.JOB_KEY: "kernel.tree",
    models.ARCHITECTURE_KEY: "job.arch",
    models.DTB_KEY: "platform.dtb",
    models.MACH_KEY: "platform.mach",
    models.FASTBOOT_KEY: "platform.fastboot",
    models.INITRD_KEY: "job.initrd_url",
    models.BOARD_KEY: "platform.name",
    models.DEVICE_TYPE_KEY: "device.type",
    models.PLAN_KEY: "test.plan",
    models.PLAN_VARIANT_KEY: "test.plan_variant",
    models.BUILD_ENVIRONMENT_KEY: "job.build_environment",
    models.FILE_SERVER_RESOURCE_KEY: "job.file_server_resource",
}

BL_META_MAP = {
    "ramdisk_addr": "initrd_addr",
    "kernel_addr": "loadaddr",
    "dtb_addr": "dtb_addr",
}

LOGIN_CASE_END_PATTERN = re.compile(r'end:.*auto-login-action.*')
TEST_CASE_SIGNAL_PATTERN = re.compile(
    r'\<LAVA_SIGNAL_TESTCASE TEST_CASE_ID.+>')


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


def _add_test_log(meta, job_log, suite):
    """Parse and save test logs

    Parse the LAVA v2 log in YAML format and save it as plain text and HTML.

    :param meta: The boot meta-data.
    :type meta: dictionary
    :param log: The kernel log in YAML format.
    :type log: string
    :param base_path: Path to the top-level directory where to store the files.
    :type base_path: string
    :param suite: Test suite name
    :type suite: string
    """
    log = yaml.load(job_log, Loader=yaml.CLoader)

    dir_path = meta[models.DIRECTORY_PATH]

    utils.LOG.info("Generating {} log files in {}".format(suite, dir_path))
    file_name = "-".join([suite, meta[models.BOARD_KEY]])
    files = tuple(".".join([file_name, ext]) for ext in ["txt", "html"])
    meta[models.BOOT_LOG_KEY], meta[models.BOOT_LOG_HTML_KEY] = files
    txt_path, html_path = (os.path.join(dir_path, f) for f in files)

    if not os.path.isdir(dir_path):
        try:
            os.makedirs(dir_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

    with codecs.open(txt_path, "w", "utf-8") as txt:
        with codecs.open(html_path, "w", "utf-8") as html:
            utils.lava_log_parser.run(log, meta, txt, html)


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
            'dt': dparser.parse(l['dt']),
            'msg': l['msg']
        }
        for l in log[start_line:end_line]
        if (l['lvl'] == 'target' and
            not TEST_CASE_SIGNAL_PATTERN.match(l['msg']))
    ]
    return lines


def _store_lava_json(job_data, meta, base_path=utils.BASE_PATH):
    """ Save the json LAVA v2 callback object

    Save LAVA v2 callback data as json file.

    :param job_data: The JSON data from the LAVA callback.
    :type job_data: dictionary
    :param meta: The boot meta-data.
    :type meta: dictionary
    :param base_path: Path to the top-level directory where to store the files.
    :type base_path: string
    """

    file_name = "-".join(["lava-json", meta[models.BOARD_KEY]])
    file_name = ".".join([file_name, "json"])

    dir_path = meta[models.DIRECTORY_PATH]

    utils.LOG.info("Saving LAVA v2 callback file {} data in {}".format(
        file_name,
        dir_path))

    file_path = os.path.join(dir_path, file_name)

    # Removing the token
    job_data.pop("token", None)

    # Add extra information
    job_data["lab_name"] = meta.get("lab_name")
    job_data["version"] = meta.get("version")
    job_data["boot_log_html"] = meta.get("boot_log_html")

    if not os.path.isdir(dir_path):
        try:
            os.makedirs(dir_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

    with open(file_path, "wb") as f:
        f.write(json.dumps(job_data))


def add_boot(job_data, job_meta, lab_name, db_options,
             base_path=utils.BASE_PATH):
    """Entry point to be used as an external task.

    This function should only be called by Celery or other task managers.
    Parse the boot data from a LAVA v2 job callback and save it along with
    kernel logs.

    :param job_data: The JSON data from the callback.
    :type job_data: dict
    :param lab_name: Name of the LAVA lab that posted the callback.
    :type lab_name: string
    :param db_options: The mongodb database connection parameters.
    :type db_options: dict
    :param base_path: Path to the top-level directory where to save files.
    :type base_path: string
    :return ObjectId The boot document id.
    """
    ret_code = 201
    doc_id = None
    errors = {}

    utils.LOG.info("Processing LAVA boot data: job {} from {}".format(
        job_data["id"], lab_name))

    if job_data.get("status") not in (COMPLETE, INCOMPLETE):
        utils.LOG.warning("Skipping LAVA job due to unsupported status: "
                          "{}".format(job_data["status_string"]))
        return None

    meta = {
        models.VERSION_KEY: "1.1",
        models.LAB_NAME_KEY: lab_name,
        models.BOOT_TIME_KEY: "0.0",
    }

    ex = None
    msg = None

    try:
        _get_job_meta(meta, job_data)
        _get_definition_meta(meta, job_meta, META_DATA_MAP_BOOT)
        _get_directory_path(meta, base_path)
        _get_lava_meta(meta, job_data)
        _store_lava_json(job_data, meta)
        _add_test_log(meta, job_data["log"], "boot")
        doc_id = utils.boot.import_and_save_boot(meta, db_options)
    except (yaml.YAMLError, ValueError) as ex:
        ret_code = 400
        msg = "Invalid LAVA data"
    except (OSError, IOError) as ex:
        ret_code = 500
        msg = "Internal error"
    finally:
        if ex is not None:
            utils.LOG.exception(ex)
        if msg is not None:
            utils.LOG.error(msg)
            utils.errors.add_error(errors, ret_code, msg)
        if errors:
            raise utils.errors.BackendError(errors)

    return doc_id


def _add_login_case(meta, results, cases, name):
    # ToDo: consolidate with _add_test_results
    tests = yaml.load(results, Loader=yaml.CLoader)
    tests_by_name = {t['name']: t for t in tests}
    login = tests_by_name.get(name)
    if not login:
        return
    test_case = {
        models.VERSION_KEY: "1.1",
        models.TIME_KEY: "0.0",
        models.INDEX_KEY: len(cases) + 1,
        models.NAME_KEY: "login",
        models.STATUS_KEY: login["result"],
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
    tests = yaml.load(results, Loader=yaml.CLoader)
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
        test_case[models.INDEX_KEY] = len(test_case_list) + 1
        test_case_list.append(test_case)

    sub_groups = []
    for index, test_set in enumerate(test_sets.iteritems(), 1):
        test_set_name, test_set_cases = test_set
        sub_group = {
            models.NAME_KEY: test_set_name,
            models.TEST_CASES_KEY: test_set_cases,
            models.INDEX_KEY: index,
        }
        sub_group.update({
            k: group[k] for k in [
                models.ARCHITECTURE_KEY,
                models.BOARD_KEY,
                models.BOOT_LOG_KEY,
                models.BOOT_LOG_HTML_KEY,
                models.BUILD_ENVIRONMENT_KEY,
                models.DEFCONFIG_FULL_KEY,
                models.DEFCONFIG_KEY,
                models.DTB_KEY,
                models.FILE_SERVER_RESOURCE_KEY,
                models.GIT_BRANCH_KEY,
                models.GIT_COMMIT_KEY,
                models.JOB_KEY,
                models.KERNEL_KEY,
                models.KERNEL_IMAGE_KEY,
                models.LAB_NAME_KEY,
                models.PLAN_VARIANT_KEY,
                models.TIME_KEY,
            ]
        })
        sub_groups.append(sub_group)

    group.update({
        models.TEST_CASES_KEY: test_cases,
        models.SUB_GROUPS_KEY: sub_groups,
    })


def _add_rootfs_info(group, base_path, file_name="build_info.json"):
    """Add rootfs info

    Parse the the JSON file with the information of the rootfs if it's
    available and add its information to the group data.  If the file URL
    matches the local storage server, then read it directly from the file
    system.

    :param group: Test group data.
    :type group: dict
    :param base_path: Path to the top-level directory where files are stored.
    :type base_path: string
    :param file_name: Name of the JSON file with the rootfs info.
    :type file_name: string
    """

    rootfs_url = group.get("initrd")
    if not rootfs_url or rootfs_url == "None":
        return

    try:
        # compare to default URL without the scheme
        _default_url = urllib2.urlparse.urlparse(DEFAULT_STORAGE_URL).netloc
        _rootfs_url = urllib2.urlparse.urlparse(rootfs_url).netloc
        if _rootfs_url.startswith(_default_url):
            rootfs_url_path = urllib2.urlparse.urlparse(rootfs_url).path
            rootfs_rel_dir = os.path.dirname(rootfs_url_path).lstrip("/")
            json_file = os.path.join(base_path, rootfs_rel_dir, file_name)
            rootfs_info_json = open(json_file)
        else:
            rootfs_top_url = rootfs_url.rpartition("/")[0]
            file_url = "/".join([rootfs_top_url, file_name])
            utils.LOG.info("Downloading rootfs info: {}".format(file_url))
            rootfs_info_json = urllib2.urlopen(file_url)

        rootfs_info = json.load(rootfs_info_json)
        group[models.INITRD_INFO_KEY] = rootfs_info
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
        _get_job_meta(meta, job_data)
        _get_definition_meta(meta, job_meta, META_DATA_MAP_TEST)
        _get_directory_path(meta, base_path)
        _get_lava_meta(meta, job_data)
        plan_name = meta[models.PLAN_KEY]
        _add_test_log(meta, job_data["log"], plan_name)
        _add_rootfs_info(meta, base_path)
        _store_lava_json(job_data, meta)
        groups = []
        cases = []
        start_log_line = 0
        log = yaml.load(job_data["log"], Loader=yaml.CLoader)
        end_lines_map = {}
        for suite_name, results in job_data["results"].iteritems():
            if suite_name == "lava":
                _add_login_case(meta, results, cases, 'auto-login-action')
                login_line_num = _get_log_line_number(log,
                                                      LOGIN_CASE_END_PATTERN)
                start_log_line = 0 if login_line_num is None \
                    else login_line_num
            else:
                suite_name = suite_name.partition("_")[2]
                group = dict(meta)
                group[models.NAME_KEY] = suite_name
                _add_test_results(group, results,
                                  end_lines_map)
                groups.append(group)
        add_log_fragments(groups, log, end_lines_map, start_log_line)

        if (len(groups) == 1) and (groups[0][models.NAME_KEY] == plan_name):
            # Only one group with same name as test plan
            plan = groups[0]
            if cases:
                insert_len = len(cases)
                plan_cases = plan[models.TEST_CASES_KEY]
                for case in plan_cases:
                    case[models.INDEX_KEY] += insert_len
                cases.extend(plan_cases)
                plan[models.TEST_CASES_KEY] = cases
        elif groups or cases:
            # Create top-level group with the test plan name
            plan = dict(meta)
            plan[models.NAME_KEY] = plan_name
            for index, group in enumerate(groups):
                group[models.INDEX_KEY] = index
            plan[models.SUB_GROUPS_KEY] = groups
            plan[models.TEST_CASES_KEY] = cases

        if plan:
            ret_code, plan_doc_id, err = \
                utils.kci_test.import_and_save_kci_tests(plan, db_options)
            utils.errors.update_errors(errors, err)
    except (yaml.YAMLError, ValueError) as ex:
        ret_code = 400
        msg = "Invalid test data from LAVA callback"
    except (OSError, IOError) as ex:
        ret_code = 500
        msg = "Internal error"
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
