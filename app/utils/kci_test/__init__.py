# Copyright (C) Collabora Limited 2017,2018,2019
# Author: Michal Galka <michal.galka@collabora.com>
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
#
# Copyright (C) Baylibre -0700,-0800,2017,2019
# Author: Khouloud Touil <ktouil@baylibre.com>
# Author: Kevin Hilman <khilman@baylibre.com>
# Author: Loys Ollivier <lollivier@baylibre.com>
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

"""Container for all the kci_test import related functions."""

import bson
import codecs
import copy
import datetime
import errno
import os
import pymongo

import models
import models.test_group as mtest_group
import models.test_case as mtest_case
import taskqueue.celery as taskc
import utils
import utils.db
import utils.errors

try:  # Py3K compat
    basestring
except NameError:
    basestring = str

# Keys that need to be checked for None or null value.
NON_NULL_KEYS_GROUP = [
    models.ARCHITECTURE_KEY,
    models.BUILD_ENVIRONMENT_KEY,
    models.DEFCONFIG_KEY,
    models.DEVICE_TYPE_KEY,
    models.GIT_BRANCH_KEY,
    models.GIT_COMMIT_KEY,
    models.JOB_KEY,
    models.KERNEL_KEY,
    models.LAB_NAME_KEY,
    models.NAME_KEY,
]

NON_NULL_KEYS_CASE = [
    models.NAME_KEY,
    models.STATUS_KEY,
]

SPEC_TEST_GROUP = {
    models.ARCHITECTURE_KEY: "arch",
    models.DEFCONFIG_FULL_KEY: "defconfig_full",
    models.DEFCONFIG_KEY: "defconfig",
    models.DEVICE_TYPE_KEY: "device_type",
    models.BUILD_ENVIRONMENT_KEY: "build_environment",
    models.GIT_BRANCH_KEY: "git_branch",
    models.GIT_COMMIT_KEY: "git_commit",
    models.INITRD_KEY: "initrd",
    models.JOB_KEY: "job",
    models.KERNEL_KEY: "kernel",
    models.LAB_NAME_KEY: "lab_name",
    models.NAME_KEY: "name",
    models.PLAN_VARIANT_KEY: "plan_variant",
}

SPEC_TEST_CASE = {
    models.KERNEL_KEY: "kernel",
    models.NAME_KEY: "name",
    models.TEST_GROUP_ID_KEY: "test_group_id",
}

# Local error function.
ERR_ADD = utils.errors.add_error


class TestImportError(Exception):
    """General test import exceptions class."""


class TestValidationError(ValueError, TestImportError):
    """General error for values of test data."""


def save_or_update(doc, spec_map, collection, database, errors):
    """Save or update the document in the database.

    Check if we have a document available in the db, and in case perform an
    update on it.

    :param doc: The document to save.
    :type doc: BaseDocument
    :param collection: The name of the collection to search.
    :type collection: str
    :param database: The database connection.
    :param errors: Where errors should be stored.
    :type errors: dict
    :return The save action return code and the doc ID.
    """
    spec = {x: getattr(doc, y) for x, y in spec_map.iteritems()}

    fields = [
        models.CREATED_KEY,
        models.ID_KEY,
    ]

    prev_doc = utils.db.find_one2(database[collection], spec, fields=fields)

    if prev_doc:
        doc_get = prev_doc.get
        doc_id = doc_get(models.ID_KEY)
        doc.id = doc_id

        utils.LOG.debug("Updating test document with id '%s'", doc_id)
        ret_val, _ = utils.db.save(database, doc)
    else:
        ret_val, doc_id = utils.db.save(database, doc)
        utils.LOG.debug("New test document with id '%s'", doc_id)

    if ret_val == 500:
        err_msg = (
            "Error saving/updating test report in the database "
            "for '%s (%s)'" %
            (
                doc.name,
                doc.id,
            )
        )
        ERR_ADD(errors, ret_val, err_msg)

    return ret_val, doc_id


def _add_test_log(dir_path, filename, log_data):
    utils.LOG.info("Generating log files in {}".format(filename))
    if not os.path.isdir(dir_path):
        try:
            os.makedirs(dir_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e
    logfile_path = os.path.join(dir_path, filename)
    with codecs.open(logfile_path, "w", "utf-8") as logfile:
        logfile.write(log_data)


def _check_for_null(test_dict, keys):
    """Check if the keys dictionary has values resembling None in its
    mandatory keys.

    Values must be different than:
    - None
    - ""
    - "null"

    :param test_dict: The dictionary to check.
    :type test_dict: dict
    :param keys: The dict of keys to parse and check for non null.
    :type keys: dict
    :raise TestValidationError if any of the keys matches the condition.
    """
    for key in keys:
        val = test_dict.get(key)
        if (val is None or
            (isinstance(val, basestring) and
                val.lower() in ('', 'null', 'none'))):
            raise TestValidationError(
                "Invalid value found for mandatory key {!r}: {!r}".format(
                    key, val))


def _get_time_as_datetime(data):
    test_time_raw = data.get(models.TIME_KEY)
    if test_time_raw is None:
        test_time_raw = 0.0
    test_time = float(test_time_raw)
    if test_time < 0.0:
        raise ValueError("Found negative test time")
    test_datetime = \
        datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=test_time)
    return test_datetime


def _update_test_case_doc_from_json(case_doc, test_case, errors):
    """Update a TestCaseDocument from the provided test dictionary.

    This function does not return anything, the TestCaseDocument passed is
    updated from the values found in the provided JSON object.

    :param case_doc: The TestCaseDocument to update.
    :type case_doc: `models.test_case.TestCaseDocument`.
    :param test_case: Test case dictionary.
    :type test_case: dict
    :param errors: Where errors should be stored.
    :type errors: dict
    """
    case_doc.time = _get_time_as_datetime(test_case)
    case_doc.arch = test_case.get(models.ARCHITECTURE_KEY)
    case_doc.build_environment = test_case.get(models.BUILD_ENVIRONMENT_KEY)
    case_doc.defconfig_full = test_case.get(models.DEFCONFIG_FULL_KEY)
    case_doc.device_type = test_case.get(models.DEVICE_TYPE_KEY)
    case_doc.git_commit = test_case.get(models.GIT_COMMIT_KEY)
    case_doc.git_branch = test_case.get(models.GIT_BRANCH_KEY)
    case_doc.index = test_case.get(models.INDEX_KEY)
    case_doc.job = test_case.get(models.JOB_KEY)
    case_doc.kernel = test_case.get(models.KERNEL_KEY)
    case_doc.lab_name = test_case.get(models.LAB_NAME_KEY)
    case_doc.log_lines = test_case.get(models.LOG_LINES_KEY, [])
    case_doc.mach = test_case.get(models.MACH_KEY)
    case_doc.measurements = test_case.get(models.MEASUREMENTS_KEY, [])
    case_doc.status = test_case[models.STATUS_KEY].upper()


def _update_test_case_doc_ids(ts_name, ts_id, case_doc, database):
    """Update test case document test group IDs references.

    :param ts_name: The test case name
    :type ts_name: str
    :param ts_id: The test case ID
    :type ts_id: str
    :param case_doc: The test case document to update.
    :type case_doc: TestCaseDocument
    :param database: The database connection to use.
    """

    # Make sure the test group ID provided is correct
    ts_oid = bson.objectid.ObjectId(ts_id)
    test_group_doc = utils.db.find_one2(database[models.TEST_GROUP_COLLECTION],
                                        ts_oid,
                                        [models.ID_KEY])
    # If exists, update the test case
    if test_group_doc:
        case_doc.test_group_id = test_group_doc.get(models.ID_KEY)
    else:
        utils.LOG.error(
            "No test group document with ID %s found for test case %s",
            ts_oid, case_doc.name)
        return None


def _parse_test_case_from_json(group_name, group_doc_id, test_case,
                               database, errors, path):
    """Parse the test case report from a JSON object.

    :param group_name: The test group name.
    :type group_name: str
    :param group_doc_id: The test group ID.
    :type group_doc_id: str
    :param test_case: The test case data.
    :type test_case: dict
    :param database: The database connection.
    :param errors: Where to store the errors.
    :type errors: dict
    :return A `models.test_case.TestCaseDocument` instance, or None if
    the JSON cannot be parsed correctly.
    """
    try:
        _check_for_null(test_case, NON_NULL_KEYS_CASE)
    except TestValidationError, ex:
        utils.LOG.exception(ex)
        ERR_ADD(errors, 400, str(ex))
        return None

    try:
        name = test_case[models.NAME_KEY]
    except KeyError, ex:
        err_msg = "Missing mandatory key in test case data"
        utils.LOG.exception(ex)
        utils.LOG.error(err_msg)
        ERR_ADD(errors, 400, err_msg)
        return None

    test_doc = mtest_case.TestCaseDocument(name)
    test_doc.created_on = datetime.datetime.now(tz=bson.tz_util.utc)
    test_doc.test_case_path = '.'.join(path + [test_doc.name])
    test_doc.plan = path[0]
    _update_test_case_doc_from_json(test_doc, test_case, errors)
    _update_test_case_doc_ids(group_name, group_doc_id, test_doc, database)
    return test_doc


def _update_test_group_doc_from_json(group_doc, group_dict, errors):
    """Update a TestGroupDocument from the provided test dictionary.

    This function does not return anything, the TestGroupDocument passed is
    updated from the values found in the provided JSON object.

    :param group_doc: The TestGroupDocument to update.
    :type group_doc: `models.test_group.TestGroupDocument`.
    :param group_dict: Test group dictionary.
    :type group_dict: dict
    :param errors: Where errors should be stored.
    :type errors: dict
    """
    group_doc.time = _get_time_as_datetime(group_dict)
    group_doc.arch = group_dict.get(models.ARCHITECTURE_KEY)
    group_doc.board_instance = group_dict.get(models.BOARD_INSTANCE_KEY)
    group_doc.boot_log = group_dict.get(models.BOOT_LOG_KEY)
    group_doc.boot_log_html = group_dict.get(models.BOOT_LOG_HTML_KEY)
    group_doc.boot_result_description = group_dict.get(
        models.BOOT_RESULT_DESC_KEY)
    group_doc.build_environment = group_dict.get(models.BUILD_ENVIRONMENT_KEY)
    group_doc.dtb = group_dict.get(models.DTB_KEY)
    group_doc.device_type = group_dict.get(models.DEVICE_TYPE_KEY)
    group_doc.defconfig = group_dict.get(models.DEFCONFIG_KEY)
    group_doc.defconfig_full = group_dict.get(models.DEFCONFIG_FULL_KEY)
    group_doc.endian = group_dict.get(models.ENDIANNESS_KEY)
    group_doc.file_server_resource = group_dict.get(
        models.FILE_SERVER_RESOURCE_KEY)
    group_doc.git_branch = group_dict.get(models.GIT_BRANCH_KEY)
    group_doc.git_commit = group_dict.get(models.GIT_COMMIT_KEY)
    group_doc.git_describe = group_dict.get(models.GIT_DESCRIBE_KEY)
    group_doc.git_url = group_dict.get(models.GIT_URL_KEY)
    group_doc.index = group_dict.get(models.INDEX_KEY)
    group_doc.initrd = group_dict.get(models.INITRD_KEY)
    group_doc.initrd_info = group_dict.get(models.INITRD_INFO_KEY)
    group_doc.job = group_dict.get(models.JOB_KEY)
    group_doc.kernel = group_dict.get(models.KERNEL_KEY)
    group_doc.kernel_image = group_dict.get(models.KERNEL_IMAGE_KEY)
    group_doc.plan_variant = group_dict.get(models.PLAN_VARIANT_KEY)
    group_doc.version = group_dict.get(models.VERSION_KEY, "1.0")
    group_doc.warnings = group_dict.get(models.BOOT_WARNINGS_KEY, 0)

    # mach_alias_key takes precedence if defined
    group_doc.mach = group_dict.get(
        models.MACH_ALIAS_KEY, group_dict.get(models.MACH_KEY))


def _update_test_group_doc_ids(group_doc, database):
    """Update test group document job and build IDs references.

    :param group_doc: The test group document to update.
    :type group_doc: TestGroupDocument
    :param database: The database connection to use.
    """
    job = group_doc.job
    kernel = group_doc.kernel
    defconfig = group_doc.defconfig
    defconfig_full = group_doc.defconfig_full
    build_env = group_doc.build_environment
    arch = group_doc.arch
    branch = group_doc.git_branch

    spec = {
        models.JOB_KEY: job,
        models.KERNEL_KEY: kernel,
        models.GIT_BRANCH_KEY: branch
    }

    job_doc = utils.db.find_one2(database[models.JOB_COLLECTION], spec)

    spec.update({
        models.ARCHITECTURE_KEY: arch,
        models.DEFCONFIG_KEY: defconfig,
        models.JOB_KEY: job,
        models.BUILD_ENVIRONMENT_KEY: build_env,
    })

    if defconfig_full:
        spec[models.DEFCONFIG_FULL_KEY] = defconfig_full

    build_doc = utils.db.find_one2(database[models.BUILD_COLLECTION], spec)

    if job_doc:
        group_doc.job_id = job_doc.get(models.ID_KEY)
    else:
        utils.LOG.warn(
            "No job document found for test group %s-%s-%s-%s (%s)",
            job, branch, kernel, defconfig_full, arch)

    if build_doc:
        doc_get = build_doc.get
        group_doc.build_id = doc_get(models.ID_KEY)

        # In case we do not have the job_id key with the previous search.
        if not group_doc.job_id:
            group_doc.job_id = doc_get(models.JOB_ID_KEY)
        if not group_doc.compiler:
            group_doc.compiler = doc_get(models.COMPILER_KEY)
        if not group_doc.compiler_version:
            group_doc.compiler_version = \
                doc_get(models.COMPILER_VERSION_KEY)
        if not group_doc.compiler_version_full:
            group_doc.compiler_version_full = \
                doc_get(models.COMPILER_VERSION_FULL_KEY)
        if not group_doc.cross_compile:
            group_doc.cross_compile = doc_get(models.CROSS_COMPILE_KEY)
        if not group_doc.modules:
            group_doc.modules = doc_get(models.MODULES_KEY)
        # Get also git information if we do not have them already,
        if not group_doc.git_branch:
            group_doc.git_branch = doc_get(models.GIT_BRANCH_KEY)
        if not group_doc.git_commit:
            group_doc.git_commit = doc_get(models.GIT_COMMIT_KEY)
        if not group_doc.git_describe:
            group_doc.git_describe = doc_get(models.GIT_DESCRIBE_KEY)
        if not group_doc.git_url:
            group_doc.git_url = doc_get(models.GIT_URL_KEY)
    else:
        utils.LOG.warn(
            "No build document found for test group %s-%s-%s-%s (%s)",
            job, branch, kernel, defconfig_full, arch)


def _parse_test_group_from_json(group_json, database, errors):
    """Parse the test group report from a JSON object.

    :param group_json: The JSON object.
    :type group_json: dict
    :param database: The database connection.
    :param errors: Where to store the errors.
    :type errors: dict
    :return A `models.test_group.TestGroupDocument` instance, or None if
    the JSON cannot be parsed correctly.
    """
    if not group_json:
        return None

    try:
        _check_for_null(group_json, NON_NULL_KEYS_GROUP)
    except TestValidationError, ex:
        utils.LOG.exception(ex)
        ERR_ADD(errors, 400, str(ex))
        return None

    try:
        name = group_json[models.NAME_KEY]
        lab_name = group_json[models.LAB_NAME_KEY]
    except KeyError, ex:
        err_msg = "Missing mandatory key in test group data"
        utils.LOG.exception(ex)
        utils.LOG.error(err_msg)
        ERR_ADD(errors, 400, err_msg)
        return None

    group_doc = mtest_group.TestGroupDocument(name, lab_name)
    group_doc.created_on = datetime.datetime.now(tz=bson.tz_util.utc)
    _update_test_group_doc_from_json(group_doc, group_json, errors)
    _update_test_group_doc_ids(group_doc, database)
    return group_doc


def update_test_group_add_test_case_id(
        case_id, group_id, group_name, database):
    """Add the test case ID to the list of a test group and save it.

    :param case_id: The ID of the test case.
    :type case_id: bson.objectid.ObjectId
    :param group_id: The ID of the group.
    :type group_id: bson.objectid.ObjectId
    :param group_name: The name of the test group.
    :type group_name: str
    :param database: The database connection.
    :type database: Database connection object.
    :return 200 if OK, 500 in case of errors; a dictionary with errors or an
    empty one.
    """

    ret_val = 200
    errors = {}

    utils.LOG.debug(
        "Updating test group '%s' (%s) with test case ID",
        group_name, str(group_id))

    ret_val = utils.db.update(
        database[models.TEST_GROUP_COLLECTION],
        {models.ID_KEY: group_id},
        {models.TEST_CASES_KEY: case_id}, operation='$push')
    if ret_val != 200:
        ADD_ERR(
            errors,
            ret_val,
            "Error updating test group '%s' with test case references" %
            (str(group_id))
        )
    return ret_val, errors


def import_and_save_test_cases(group_doc_id, group_name, test_cases,
                               database, errors, path):
    """Import the tests cases from a JSON object into a group.

    Parse the test_cases JSON data into a list of test cases, add them to the
    database and update the related test group.

    This function returns an operation code based on the import result
    of all the test cases.

    :param group_doc_id: The related test group ID.
    :type group_doc_id: str
    :param group_name: The related test group name.
    :type group_name: str
    :param test_cases: The JSON object with incoming test cases data.
    :type test_cases: dict
    :param database: The database connection.
    :param errors: Where errors should be stored.
    :type errors: dict
    :return the operation code (201 if success, 500 in case of an error).
    """
    ret_code = 500

    if not all((group_doc_id, group_name, test_cases)):
        return ret_code

    for test_case in test_cases:
        tc_doc = _parse_test_case_from_json(group_name, group_doc_id,
                                            test_case, database, errors, path)
        if tc_doc:
            ret_code, tc_doc_id = save_or_update(
                tc_doc, SPEC_TEST_CASE, models.TEST_CASE_COLLECTION,
                database, errors)

        if ret_code == 500:
            err_msg = (
                "Error saving test case report in the database "
                "for '%s (%s, %s)'" %
                (
                    tc_doc.name,
                    tc_doc.status,
                    tc_doc.test_group_id,
                )
            )
            ERR_ADD(errors, ret_code, err_msg)
            return ret_code
        else:
            # Test case imported successfully update test group
            ret_code, errors = update_test_group_add_test_case_id(
                tc_doc_id, group_doc_id, group_name, database)

    return ret_code


def update_test_group_add_sub_group_id(
        group_id, group_name, sub_group_id, database):
    """Add sub-group ID to the list in a parent test group and save it.

    :param group_id: The ID of the test group.
    :type case_id: bson.objectid.ObjectId
    :param group_name: The name of the test group.
    :type group_name: str
    :param sub_group_id: The ID of the sub-group.
    :type sub_group_id: bson.objectid.ObjectId
    :param database: The database connection.
    :type database: Database connection object.
    :return 200 if OK, 500 in case of errors; a dictionary with errors or an
    empty one.
    """

    ret_val = 200
    errors = {}

    utils.LOG.debug(
        "Updating test group '{}' ({}) with sub-group ID {}".format(
            group_name, str(group_id), sub_group_id))

    ret_val = utils.db.update(
        database[models.TEST_GROUP_COLLECTION],
        {models.ID_KEY: group_id},
        {models.SUB_GROUPS_KEY: sub_group_id}, operation='$push')
    if ret_val != 200:
        ADD_ERR(
            errors,
            ret_val,
            "Error updating test group '%s' with test group references" %
            (str(group_id))
        )
    return ret_val, errors


def import_and_save_test_group(group, parent_id, database, errors, path=None):
    """Import a test group from a JSON object

    Parse the group JSON data into a TestGroupDocument object.

    This function returns an operation code based on the import result
    of all the test cases.

    :param group: The test group data.
    :type group_doc: dict
    :param parent_id: The parent test group document ID.
    :type parent_id: str
    :param database: The database connection.
    :param errors: Where errors should be stored.
    :type errors: dict
    :return The document ID or None if an error occurred.
    """
    group_doc_id = None
    group_doc = _parse_test_group_from_json(group, database, errors)

    if not group_doc or errors:
        utils.LOG.warn("Failed to parse test group JSON data")
        return None

    path = list(path) if path else list()
    path.append(group_doc.name)

    group_doc.parent_id = parent_id

    ret_code, group_doc_id = save_or_update(
        group_doc, SPEC_TEST_GROUP, models.TEST_GROUP_COLLECTION,
        database, errors)

    test_cases = group.get(models.TEST_CASES_KEY)
    if test_cases:
        ret_code = import_and_save_test_cases(
            group_doc_id, group_doc.name, test_cases, database, errors, path)

    sub_groups = group.get(models.SUB_GROUPS_KEY)
    if sub_groups:
        for sub_group in sub_groups:
            sub_group_doc_id = import_and_save_test_group(
                sub_group, group_doc_id, database, errors, path)
            if not sub_group_doc_id:
                utils.LOG.warn("Failed to parse sub-group")
                return None
            update_test_group_add_sub_group_id(
                group_doc_id, group_doc.name, sub_group_doc_id, database)

    return group_doc_id


def import_and_save_kci_tests(group, db_options, base_path=utils.BASE_PATH):
    """Wrapper function to be used as an external task.

    This function should only be called by Celery or other task managers.
    Import and save the test report as found from the parameters in the
    provided JSON object.

    :param group: The JSON group data.
    :type test_group_obj: dict
    :param db_options: The mongodb database connection parameters.
    :type db_options: dict
    :param base_path: The base path on the file system where data is stored.
    :type base_path: str
    :return operation code (201 if success, 500 in case of an error), the group
    document ID and a dictionary with errors.
    """
    group_doc_id = None
    ret_code = 500
    errors = {}

    try:
        db = utils.db.get_db_connection(db_options)
        group_doc_id = import_and_save_test_group(group, None, db, errors)

        if not group_doc_id:
            utils.LOG.warn("No test group report imported nor saved")
        else:
            def _count(group, n_groups, n_tests):
                n_tests += len(group[models.TEST_CASES_KEY])
                sub_groups = group.get(models.SUB_GROUPS_KEY)
                if sub_groups:
                    n_groups += len(sub_groups)
                    for sub in sub_groups:
                        n_groups, n_tests = _count(sub, n_groups, n_tests)
                return n_groups, n_tests
            n_groups, n_tests = _count(group, 1, 0)
            utils.LOG.info("Imported {} tests in {} groups from {}".format(
                n_tests, n_groups, group[models.NAME_KEY]))

            ret_code = 201
            # TODO fix this: need to define a save_to_disk method
            # save_to_disk(ts_doc, test_group_obj, base_path, errors)
    except pymongo.errors.ConnectionFailure, ex:
        utils.LOG.exception(ex)
        utils.LOG.error("Error getting database connection")
        ERR_ADD(errors, 500, "Error connecting to the database")

    return ret_code, group_doc_id, errors
