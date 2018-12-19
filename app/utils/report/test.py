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

"""Create the tests email report."""

import json
import os

import models
import utils
import utils.db
import utils.report.common as rcommon

TEST_REPORT_FIELDS = [
    models.ARCHITECTURE_KEY,
    models.BOARD_INSTANCE_KEY,
    models.BOARD_KEY,
    models.BOOT_ID_KEY,
    models.BOOT_LOG_HTML_KEY,
    models.BOOT_LOG_KEY,
    models.BUILD_ID_KEY,
    models.CREATED_KEY,
    models.DEFCONFIG_FULL_KEY,
    models.DEFCONFIG_KEY,
    models.DEFINITION_URI_KEY,
    models.DEVICE_TYPE_KEY,
    models.GIT_BRANCH_KEY,
    models.GIT_COMMIT_KEY,
    models.GIT_DESCRIBE_KEY,
    models.GIT_URL_KEY,
    models.ID_KEY,
    models.INITRD_KEY,
    models.INITRD_INFO_KEY,
    models.JOB_ID_KEY,
    models.JOB_KEY,
    models.KERNEL_KEY,
    models.LAB_NAME_KEY,
    models.METADATA_KEY,
    models.NAME_KEY,
    models.STATUS_KEY,
    models.TEST_CASES_KEY,
    models.SUB_GROUPS_KEY,
    models.TIME_KEY,
    models.VCS_COMMIT_KEY,
    models.VERSION_KEY,
]


def _get_case(list_cases, name):
    """Look for a test case with a given name

    :param list_case: List of test cases from  test group
    :type list_case: list
    :param name: Name of a test case
    :type name: string
    """

    for d in list_cases:
        if d['name'] == name:
            return d


def create_regressions_data(test_docs, test_data):
    """Create the regressions data for the email report.

    Will create a dictionary with all the regressions

    :param test_docs: The regressions data (the list of tests).
    :type test_docs: list
    :param test_data: Details about the test results
    :type test_data: dict
    :return dict The regressions results in a dictionary.
    """
    regr_dict = {}

    # Make sure the test reports in the regressions data structure are
    # correctly sorted by date, so that the oldest document is the PASS one
    # and the most recent one is the last FAIL-ed.
    test_docs.sort(
        cmp=lambda x, y: cmp(x[models.CREATED_KEY], y[models.CREATED_KEY]))

    ndocs = len(test_docs)
    last_good = test_docs[0]

    # Check case by case when was the first time it failed
    for tc in last_good["test_cases"]:
        for i in range(ndocs-1, 0, -1):
            post = test_docs[i]
            prev = test_docs[i-1]
            post_case = _get_case(post["test_cases"], tc["name"])
            prev_case = _get_case(prev["test_cases"], tc["name"])

            if prev_case["status"] == ['PASS'] and post_case["status"] == 'FAIL':
                msg = "last worked in"
                d = {tc["name"]: "{} {}".format(msg, prev["git_describe"])}
                regr_dict.update(d)
                continue

            if prev_case["status"] == ['SKIP'] and post_case["status"] == 'FAIL':
                msg = "new FAIL, skipped in"
                d = {tc["name"]: "{} {}".format(msg, prev["git_describe"])}
                regr_dict.update(d)
                continue

    return regr_dict


def parse_regressions(lab_regressions, group_data):
    """Parse the regressions data and create a dictionary with the
    regressions for the report. The dictionary has the test name as key
    and the last kernel were it worked as value.

    The returned data structure is:

        {
            "data": {
                 'test name 1': 'v4.20-rc4-301-g13294fbcd4c1',
                 'test name 2': 'v4.20-rc4-300-g34caf313b358',
                 ...
            }
        }

    :param lab_regressions: The regressions data for each lab.
    :type lab_regressions: dict
    :param group_data: Details about the test results
    :type group_data: dict
    :return dict The regressions data structure for the report.
    """
    regressions = {}
    lab_name = group_data.get("lab_name", None)
    arch_name = group_data.get("arch", None)
    board_name = group_data.get("board", None)

    for lab, lab_d in lab_regressions.iteritems():
        if lab_name and lab != lab_name:
            continue

        for arch, arch_d in lab_d.iteritems():
            if arch_name and arch_name != arch:
                continue

            for board, board_d in arch_d.iteritems():
                if board_name and board_name != board:
                    continue

                for instance_d in board_d.itervalues():
                    for defconfig, defconfig_d in instance_d.iteritems():
                        for compiler, tests in defconfig_d.iteritems():
                            regr = create_regressions_data(tests, group_data)
                            regressions.update({"data": regr})

    return regressions


def _add_test_group_data(group, database):
    test_cases = []
    for test_case_id in group[models.TEST_CASES_KEY]:
        test_case = utils.db.find_one2(
           database[models.TEST_CASE_COLLECTION],
           {"_id": test_case_id})
        test_cases.append(test_case)

    sub_groups = []
    for sub_group_id in group[models.SUB_GROUPS_KEY]:
        sub_group = utils.db.find_one2(
            database[models.TEST_GROUP_COLLECTION],
            {"_id": sub_group_id})
        _add_test_group_data(sub_group, database)
        sub_groups.append(sub_group)

    total = {status: 0 for status in ["PASS", "FAIL", "SKIP"]}

    for test_case in test_cases:
        total[test_case["status"]] += 1

    for sub_group_total in (sg["total"] for sg in sub_groups):
        for status, count in sub_group_total.iteritems():
            total[status] += count

    # Check regressions
    reg_doc = database[models.TEST_GROUP_REGRESSIONS_COLLECTION].find_one(
        {models.JOB_KEY: group[models.JOB_KEY],
         models.KERNEL_KEY: group[models.KERNEL_KEY],
         models.GIT_BRANCH_KEY: group[models.GIT_BRANCH_KEY],
         models.NAME_KEY: group[models.NAME_KEY]})

    if reg_doc:
        regressions = parse_regressions(reg_doc[models.REGRESSIONS_KEY], group)
    else:
        regressions = None

    group.update({
        "test_cases": test_cases,
        "sub_groups": sub_groups,
        "total_tests": sum(total.values()),
        "total": total,
        "regressions": regressions,
    })


def create_test_report(data, email_format, db_options,
                       base_path=utils.BASE_PATH):
    """Create the tests report email to be sent.

    :param data: The meta-data for the test job.
    :type data: dictionary
    :param email_format: The email format to send.
    :type email_format: list
    :param db_options: The mongodb database connection parameters.
    :type db_options: dict
    :param base_path: Path to the top-level storage directory.
    :type base_path: string
    :return A tuple with the TXT email body, the HTML email body and the
    headers as dictionary.  If an error occured, None.
    """
    database = utils.db.get_db_connection(db_options)

    job, branch, kernel, plans = (data[k] for k in [
        models.JOB_KEY,
        models.GIT_BRANCH_KEY,
        models.KERNEL_KEY,
        models.PLANS_KEY
    ])

    # Avoid using the field "plans" when fetching the documents
    # from mongodb
    del data['plans']

    specs = {x: data[x] for x in data.keys() if data[x]}

    test_group_docs = list(utils.db.find(
        database[models.TEST_GROUP_COLLECTION],
        spec=specs,
        fields=TEST_REPORT_FIELDS))

    top_groups = []
    sub_group_ids = []

    for group in test_group_docs:
        sub_group_ids.extend(group[models.SUB_GROUPS_KEY])

    top_groups = []
    for group in test_group_docs:
        if group["_id"] not in sub_group_ids and  \
           group["name"] != "lava" and \
           not plans:
            top_groups.append(group)
        elif plans and group["name"] in plans:
            top_groups.append(group)

    if not top_groups:
        utils.LOG.warning("Failed to find test group documents")
        return None

    for group in top_groups:
        _add_test_group_data(group, database)

    if not plans:
        plans_string = "All the results are included"
        subject_str = "Test results for {}/{} - {}".format(job, branch, kernel)
    else:
        plans_string = ", ".join(plans)
        subject_str = "Test results ({}) for {}/{} - {}".format(plans_string,
                                                                job,
                                                                branch,
                                                                kernel)

    git_url, git_commit = (top_groups[0][k] for k in [
        models.GIT_URL_KEY, models.GIT_COMMIT_KEY])

    headers = {
        rcommon.X_REPORT: rcommon.TEST_REPORT_TYPE,
        rcommon.X_BRANCH: branch,
        rcommon.X_TREE: job,
        rcommon.X_KERNEL: kernel,
    }

    template_data = {
        "subject_str": subject_str,
        "tree": job,
        "branch": branch,
        "git_url": git_url,
        "kernel": kernel,
        "git_commit": git_commit,
        "plans_string": plans_string,
        "boot_log": models.BOOT_LOG_KEY,
        "boot_log_html": models.BOOT_LOG_HTML_KEY,
        "storage_url": rcommon.DEFAULT_STORAGE_URL,
        "test_groups": top_groups,
    }

    if models.EMAIL_TXT_FORMAT_KEY in email_format:
        txt_body = rcommon.create_txt_email("test.txt", **template_data)
    else:
        txt_body = None

    if models.EMAIL_HTML_FORMAT_KEY in email_format:
        html_body = rcommon.create_html_email("test.html", **template_data)
    else:
        html_body = None

    return txt_body, html_body, subject_str, headers
