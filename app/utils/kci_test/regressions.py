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

"""Logic to find regressions in test groups reports."""

import bson
import redis

import models
import utils
import utils.database.redisdb as redisdb
import utils.db

# How the key to access the regressions data structure is formatted.
# Done in this way so that we can use mongodb dot notation to access embedded
# documents.
REGRESSION_FMT = "{lab:s}.{arch:s}.{board:s}.{instance:s}.{defconfig:s}.{compiler:s}"
# The real data structure is accessed with the name of the key followed by
# the rest of the embedded document key.
REGRESSION_DOT_FMT = "{name_key:s}.{document_key:s}"
# Lock key format for the Redis lock.
LOCK_KEY_FMT = "test-group-regressions-{job:s}-{branch:s}-{kernel:s}-{name:s}"


def sanitize_key(key):
    """Remove and replace invalid characters from a key.

    MongoDB's document keys must not contain some special characters.

    :param key: The key to sanitize.
    :type key: str
    :return str The sanitized key.
    """
    sanitized = key
    if key:
        sanitized = key.replace(" ", "").replace(".", ":")

    return sanitized


def create_regressions_key(test_group_doc):
    """Generate the regressions key for this test group report.

    :param test_group_doc: The test group report document.
    :type test_group_doc: dict
    :return str The test group regression key.
    """
    b_get = test_group_doc.get

    arch = b_get(models.ARCHITECTURE_KEY)
    b_instance = \
        sanitize_key(str(b_get(models.BOARD_INSTANCE_KEY)).lower())
    board = sanitize_key(b_get(models.BOARD_KEY))
    compiler = sanitize_key(str(b_get(models.COMPILER_VERSION_EXT_KEY)))
    defconfig = sanitize_key(b_get(models.DEFCONFIG_FULL_KEY))
    lab = b_get(models.LAB_NAME_KEY)

    return REGRESSION_FMT.format(lab=lab,
                                 arch=arch,
                                 board=board,
                                 instance=b_instance,
                                 defconfig=defconfig,
                                 compiler=compiler)


def get_regressions_by_key(key, regressions):
    """From a formatted key, get the actual regressions list.

    :param key: The key we need to look up.
    :type key: str
    :param regressions: The regressions data structure.
    :type regressions: dict
    :return list The regressions for the passed key.
    """
    k = key.split(".")
    regr = []
    try:
        regr = regressions[k[0]][k[1]][k[2]][k[3]][k[4]][k[5]]
    except (IndexError, KeyError):
        utils.LOG.error("Error retrieving regressions with key: %s", key)

    return regr


def gen_regression_keys(regressions):
    """Go through the regression data structure and yield the "keys".

    The regression data structure is a dictionary with nested dictionaries.

    :param regressions: The data structure that contains the regressions.
    :type regressions: dict
    :return str The regression key.
    """
    for lab in regressions.viewkeys():
        lab_d = regressions[lab]

        for arch in lab_d.viewkeys():
            arch_d = lab_d[arch]

            for board in arch_d.viewkeys():
                board_d = arch_d[board]

                for b_instance in board_d.viewkeys():
                    instance_d = board_d[b_instance]

                    for defconfig in instance_d.viewkeys():
                        defconfig_d = instance_d[defconfig]

                        for compiler in defconfig_d.viewkeys():
                            yield REGRESSION_FMT.format(lab=lab,
                                                        arch=arch,
                                                        board=board,
                                                        instance=b_instance,
                                                        defconfig=defconfig,
                                                        compiler=compiler)


def check_prev_regression(last_test_group, prev_test_group, db_options):
    """Check if we have a previous regression document.

    Make sure that the test group we are looking for already has a key in a
    regression document.

    It will return a 2-tuple:
    - (None, None) if nothing is found;
    - (regr_doc_id, None) if we already have a regression document, but the
      test group report is not tracked in there;
    - (regr_doc_id, regr_list) if we have a regressions document and the test
      group report is already tracked.

    :param last_test_group: The test group we are looking at.
    :type last_test_group: dict
    :param prev_test_group: The previous test group report.
    :type prev_test_group: dict
    :param db_options: The database connection parameters.
    :type db_options: dict
    :return A 2-tuple: The ID of the regression document, and the list of
    all previous regressions.
    """
    ret_val = (None, None)
    p_get = prev_test_group.get

    spec = {
        models.GIT_BRANCH_KEY: p_get(models.GIT_BRANCH_KEY),
        models.JOB_KEY: p_get(models.JOB_KEY),
        models.KERNEL_KEY: p_get(models.KERNEL_KEY),
        models.NAME_KEY: p_get(models.NAME_KEY)
    }
    if prev_test_group[models.JOB_ID_KEY]:
        spec[models.JOB_ID_KEY] = p_get(models.JOB_ID_KEY)

    prev_regr_doc = utils.db.find_one3(
        models.TEST_GROUP_REGRESSIONS_COLLECTION, spec, db_options=db_options)

    if prev_regr_doc:
        prev_regr = prev_regr_doc[models.REGRESSIONS_KEY]

        test_group_regr_key = create_regressions_key(last_test_group)
        if test_group_regr_key in gen_regression_keys(prev_regr):
            ret_val = (prev_regr_doc[models.ID_KEY], prev_regr)
        else:
            ret_val = (prev_regr_doc[models.ID_KEY], None)

    return ret_val


# pylint: disable=too-many-locals
def track_regression(test_group_doc, pass_doc, old_regr, db_options):
    """Track the regression for the provided test group report.

    :param test_group_doc: The test group document where we have a regression.
    :type test_group_doc: dict
    :param pass_doc: The previous test group document, when we start tracking a
    regression.
    :type pass_doc: dict
    :param old_regr: The previous regressions document.
    :type old_regr: 2-tuple
    :param db_options: The database connection parameters.
    :type db_options: dict
    :return tuple The status code (200, 201, 500); and the regression
    document id.
    """
    ret_val = 201
    doc_id = None

    regr_key = create_regressions_key(test_group_doc)

    b_get = test_group_doc.get
    test_group_id = b_get(models.ID_KEY)
    arch = b_get(models.ARCHITECTURE_KEY)
    b_instance = sanitize_key(str(b_get(models.BOARD_INSTANCE_KEY)).lower())
    board = sanitize_key(b_get(models.BOARD_KEY))
    compiler = sanitize_key(str(b_get(models.COMPILER_VERSION_EXT_KEY)))
    defconfig = sanitize_key(b_get(models.DEFCONFIG_FULL_KEY))
    job = b_get(models.JOB_KEY)
    job_id = b_get(models.JOB_ID_KEY)
    kernel = b_get(models.KERNEL_KEY)
    lab = b_get(models.LAB_NAME_KEY)
    created_on = b_get(models.CREATED_KEY)
    branch = b_get(models.GIT_BRANCH_KEY)
    name = b_get(models.NAME_KEY)

    # We might be importing test group in parallel through multi-processes.
    # Keep a lock here when looking for the previous regressions or we might
    # end up with multiple test group regression creations.
    redis_conn = redisdb.get_db_connection(db_options)
    lock_key = LOCK_KEY_FMT.format(job=job,
                                   branch=branch,
                                   kernel=kernel,
                                   name=name)

    with redis.lock.Lock(redis_conn, lock_key, timeout=5):
        # Do we have "old" regressions?
        regr_docs = []
        if all([old_regr, old_regr[0]]):
            regr_docs = get_regressions_by_key(
                regr_key, old_regr[1])

        if pass_doc:
            regr_docs.append(pass_doc)

        # Append the actual fail test group report to the list.
        regr_docs.append(test_group_doc)

        # Do we have already a regression registered for this job_id,
        # job, kernel?
        prev_reg_doc = check_prev_regression(test_group_doc,
                                             test_group_doc,
                                             db_options)
        if prev_reg_doc[0]:
            doc_id = prev_reg_doc[0]

            regr_data_key = \
                REGRESSION_DOT_FMT.format(name_key=models.REGRESSIONS_KEY,
                                          document_key=regr_key)

            if prev_reg_doc[1]:
                # If we also have the same key in the document, append the
                # new test group report.
                document = {"$addToSet": {regr_data_key: test_group_doc}}
            else:
                # Otherwise just set the new key.
                document = {"$set": {regr_data_key: regr_docs}}

            ret_val = utils.db.update3(
                models.TEST_GROUP_REGRESSIONS_COLLECTION,
                {models.ID_KEY: prev_reg_doc[0]},
                document,
                db_options=db_options
            )
        else:
            regression_doc = {
                models.CREATED_KEY: created_on,
                models.GIT_BRANCH_KEY: branch,
                models.JOB_ID_KEY: job_id,
                models.JOB_KEY: job,
                models.KERNEL_KEY: kernel,
                models.NAME_KEY: name
            }

            # The regression data structure.
            # A dictionary with nested keys, whose keys in nested order are:
            # lab name
            # architecture type
            # board name
            # board instance or the string "none"
            # defconfig full string
            # compiler string (just compiler + version)
            # The regressions are stored in a list as the value of the
            # "compiler" key.
            regression_doc[models.REGRESSIONS_KEY] = {
                lab: {
                    arch: {
                        board: {
                            b_instance: {
                                defconfig: {
                                    compiler: regr_docs
                                }
                            }
                        }
                    }
                }
            }

            ret_val, doc_id = \
                utils.db.save3(
                    models.TEST_GROUP_REGRESSIONS_COLLECTION, regression_doc,
                    db_options=db_options)

        # Save the regressions id and test group id in an index collection.
        if all([any([ret_val == 201, ret_val == 200]), doc_id]):
            utils.db.save3(
                models.TEST_GROUP_REGRESSIONS_BY_TEST_GROUP_COLLECTION,
                {
                    models.TEST_GROUP_ID_KEY: test_group_id,
                    models.TEST_GROUP_REGRESSIONS_ID_KEY: doc_id,
                    models.CREATED_KEY: created_on
                },
                db_options=db_options
            )

    return ret_val, doc_id


def check_and_track(test_group_doc, db_options):
    """Check previous test group report and start tracking regressions
    for that group report. This function won't take care of the sub_groups
    only of the top group.

    :param test_group_doc: The test group document we are working on.
    :type test_group_doc: dict
    :param conn: The database connection.
    :param db_options: The database connection parameters.
    :type db_options: dict
    :return tuple The return value; and the regression document id.
    """
    ret_val = None
    doc_id = None

    b_get = test_group_doc.get
    # Look for an older and as much similar as possible test group report.
    # In case the test group report we are analyzing is FAIL and the old one
    # is PASS, it's a new regression that we need to track.
    spec = {
        models.ARCHITECTURE_KEY: b_get(models.ARCHITECTURE_KEY),
        models.BOARD_KEY: b_get(models.BOARD_KEY),
        models.COMPILER_VERSION_EXT_KEY:
            b_get(models.COMPILER_VERSION_EXT_KEY),
        models.CREATED_KEY: {"$lt": b_get(models.CREATED_KEY)},
        models.DEFCONFIG_FULL_KEY: b_get(models.DEFCONFIG_FULL_KEY),
        models.DEFCONFIG_KEY: b_get(models.DEFCONFIG_KEY),
        models.GIT_BRANCH_KEY: b_get(models.GIT_BRANCH_KEY),
        models.JOB_KEY: b_get(models.JOB_KEY),
        models.LAB_NAME_KEY: b_get(models.LAB_NAME_KEY),
        models.NAME_KEY: b_get(models.NAME_KEY),
    }

    old_doc = utils.db.find_one3(
        models.TEST_GROUP_COLLECTION, spec, sort=[(models.CREATED_KEY, -1)])

    if old_doc:
        database = utils.db.get_db_connection(db_options)
        _add_test_group_data(old_doc, database)

        # If previous test failed this is a number higher than 0
        if old_doc.get('total').get('FAIL') != 0:
            # "Old" regression case, we might have to keep track of it.
            utils.LOG.info("Previous test group report failed,"
                           "checking previous regressions")

            # Check if we have old regressions first.
            # If not, we don't track it since it's the first time we
            # know about it.
            prev_reg = check_prev_regression(test_group_doc,
                                             old_doc,
                                             db_options)

            if all([prev_reg[0], prev_reg[1]]):
                utils.LOG.info("Found previous regressions, keep tracking")
                ret_val, doc_id = track_regression(
                    test_group_doc, None, prev_reg, db_options)
            else:
                utils.LOG.info("No previous regressions found, not tracking")
        # Previous test didn't fail, this is a NEW regression
        else:
            # New regression case.
            utils.LOG.info("Previous test group report passed, start tracking")
            ret_val, doc_id = track_regression(
                test_group_doc, old_doc, (None, None), db_options)
    else:
        utils.LOG.info("No previous test group report found, not tracking")

    return ret_val, doc_id


def _add_test_group_data(group, database):
    """Replace the test_case and subgroups with the full information.
    about the test cases and test groups respectively

    :param group: The test group document we are working on.
    :type group: dict
    :param database: The database connection.
    """
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

    group.update({
        "test_cases": test_cases,
        "sub_groups": sub_groups,
        "total_tests": sum(total.values()),
        "total": total,
    })


def find(test_group_id, db_options):
    """Find the regression starting from a single test group report.

    :param test_group_id: The id of the test group document.
                          Must be a valid ObjectId.
    :type test_group_id: str, ObjectId
    :param db_options: The database connection parameters.
    :type db_options: dict
    :return tuple The return value that can be 200, 201 or 500; the Id of the
    regression document or None.
    """
    results = (None, None)

    utils.LOG.info("Searching test group regressions for '%s'",
                   str(test_group_id))

    if not isinstance(test_group_id, bson.objectid.ObjectId):
        try:
            test_group_id = bson.objectid.ObjectId(test_group_id)
        except bson.errors.InvalidId:
            test_group_id = None
            utils.LOG.info("Error converting test group id '%s'",
                           str(test_group_id))

    test_group_doc = utils.db.find_one3(
        models.TEST_GROUP_COLLECTION, test_group_id, db_options=db_options)

    if test_group_doc:
        database = utils.db.get_db_connection(db_options)
        _add_test_group_data(test_group_doc, database)
        test_group_doc_failed = test_group_doc.get('total').get('FAIL')

    if test_group_doc and test_group_doc_failed > 0:
        # First check the top group
        regressions_id = utils.db.find_one3(
            models.TEST_GROUP_REGRESSIONS_BY_TEST_GROUP_COLLECTION,
            {models.TEST_GROUP_ID_KEY: test_group_id},
            db_options=db_options)

        if regressions_id:
            utils.LOG.info("Test regressions regressions are already "
                           "tracked for {}".format(test_group_id))
        else:
            results = check_and_track(test_group_doc, db_options)

            # Then we check the sub_groups, if any
            sub_groups = test_group_doc["sub_groups"]
            if sub_groups:
                for sg in sub_groups:
                    utils.LOG.info("Checking sub group: {}".format(sg['name']))
                    if sg.get('total').get('FAIL') > 0:
                        # Check if it's already tracked
                        results = check_and_track(sg, db_options)
                    else:
                        utils.LOG.info("Nothing to track for sub group: "
                                       "{}".format(sg['name']))
    else:
        utils.LOG.info("No test group doc or not failed test group report")

    return results
