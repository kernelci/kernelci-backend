# Copyright (C) Collabora Limited 2019, 2023
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
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

"""All test bisection operations."""

import copy
import datetime
import random
from itertools import chain

import bson
import jenkins

import models
import utils
import utils.db


def _find_regressions(job, branch, kernel, plan, db):
    regr_collection = db[models.TEST_REGRESSION_COLLECTION]
    spec = {
        models.JOB_KEY: job,
        models.GIT_BRANCH_KEY: branch,
        models.KERNEL_KEY: kernel,
        '.'.join([models.HIERARCHY_KEY, '0']): plan,
    }
    all_regressions = utils.db.find(regr_collection, spec=spec)
    regressions = dict()
    for regr in all_regressions:
        rlist = regressions.setdefault(regr[models.TEST_CASE_PATH_KEY], list())
        rlist.append(regr)
    return regressions


def _shrink_regressions(regressions_list):
    rlist = copy.copy(regressions_list)
    random.shuffle(rlist)
    return rlist[:3]


def _filter_regressions_by_tree(regressions, trees):
    print("FILTER TREES")
    return list(
        reg for reg in regressions
        if reg.job in trees
    )


def _create_bisection(regr, db):
    regr_data = regr[models.REGRESSIONS_KEY]
    good, bad = (regr_data[r] for r in (0, -1))
    spec = {x: regr[x] for x in [
        models.TEST_CASE_PATH_KEY,
        models.DEVICE_TYPE_KEY,
        models.ARCHITECTURE_KEY,
        models.DEFCONFIG_FULL_KEY,
    ]}
    spec.update({
        models.BISECT_GOOD_COMMIT_KEY: good[models.GIT_COMMIT_KEY],
        models.BISECT_BAD_COMMIT_KEY: bad[models.GIT_COMMIT_KEY],
    })
    doc = utils.db.find_one2(db[models.BISECT_COLLECTION], spec)
    if doc:
        return doc

    doc = models.bisect.TestCaseBisectDocument()
    doc.version = "1.0"
    doc.created_on = datetime.datetime.now(tz=bson.tz_util.utc)

    doc.test_case_path = regr[models.TEST_CASE_PATH_KEY]
    doc.regression_id = regr[models.ID_KEY]
    doc.device_type = regr[models.DEVICE_TYPE_KEY]
    doc.lab_name = bad[models.LAB_NAME_KEY]
    doc.plan_variant = bad[models.PLAN_VARIANT_KEY]

    doc.good_commit = good[models.GIT_COMMIT_KEY]
    doc.good_commit_url = regr[models.GIT_URL_KEY]
    doc.good_commit_date = good[models.CREATED_KEY]
    doc.bad_commit = bad[models.GIT_COMMIT_KEY]
    doc.bad_commit_url = regr[models.GIT_URL_KEY]
    doc.bad_commit_date = bad[models.CREATED_KEY]
    doc.job = regr[models.JOB_KEY]
    doc.kernel = regr[models.KERNEL_KEY]
    doc.git_branch = regr[models.GIT_BRANCH_KEY]
    doc.git_url = regr[models.GIT_URL_KEY]
    doc.arch = regr[models.ARCHITECTURE_KEY]
    doc.defconfig_full = regr[models.DEFCONFIG_FULL_KEY]
    doc.compiler = regr[models.COMPILER_KEY]
    doc.compiler_version = regr[models.COMPILER_VERSION_KEY]
    doc.build_environment = regr[models.BUILD_ENVIRONMENT_KEY]
    doc.build_id = bad[models.BUILD_ID_KEY]
    utils.bisect.common.save_bisect_doc(db, doc, regr[models.ID_KEY])
    return doc.to_dict()


def _start_bisection(bisection, jopts):
    params_map = {
        "KERNEL_URL": models.GIT_URL_KEY,
        "KERNEL_BRANCH": models.GIT_BRANCH_KEY,
        "KERNEL_TREE": models.JOB_KEY,
        "KERNEL_NAME": models.KERNEL_KEY,
        "GOOD_COMMIT": models.BISECT_GOOD_COMMIT_KEY,
        "BAD_COMMIT": models.BISECT_BAD_COMMIT_KEY,
        "ARCH": models.ARCHITECTURE_KEY,
        "DEFCONFIG": models.DEFCONFIG_FULL_KEY,
        "TARGET": models.DEVICE_TYPE_KEY,
        "BUILD_ENVIRONMENT": models.BUILD_ENVIRONMENT_KEY,
        "LAB": models.LAB_NAME_KEY,
        "TEST_PLAN_VARIANT": models.PLAN_VARIANT_KEY,
        "TEST_CASE": models.TEST_CASE_PATH_KEY,
    }
    params = {
        k: v for (k, v) in (
            (k, bisection.get(x)) for k, x in params_map.iteritems()) if v
    }
    utils.LOG.info("Triggering bisection for {}/{}: {} on {} in {}".format(
        params["KERNEL_TREE"], params["KERNEL_BRANCH"],
        params["TEST_CASE"], params["TARGET"], params["LAB"]))
    server = jenkins.Jenkins(jopts["url"], jopts["user"], jopts["token"])
    server.build_job(jopts["bisect"], params)


def trigger_bisections(job, branch, kernel, plan,
                       db_options=None, jenkins_options=None):
    """Trigger Jenkins bisections for each document that matches

    No more than 3 bisections will be run for the same combination of test case
    path and kernel build.

    :param job: Job name (i.e. tree name)
    :type job: str
    :param branch: Git branch name
    :type branch: str
    :param plan: Test plan name
    :type plan: str
    :param db_options: The database connection parameters
    :type db_options: dict
    :param jenkins_options: The Jenkins connection parameters
    :type jenkins_options: dict
    """
    db = utils.db.get_db_connection(db_options)
    all_regressions = _find_regressions(job, branch, kernel, plan, db)
    print("ALL REGRESSIONS:", all_regressions)
    trees = jenkins_options.get('bisection-git-trees')
    print("TREES", trees)
    if trees:
        all_regressions = _filter_regressions_by_tree(all_regressions, trees)
    print("FILTERED REGRESSIONS:", all_regressions)
    shrunk_regressions = {
        key: _shrink_regressions(regr_list)
        for key, regr_list in all_regressions.iteritems()
    }
    regressions = [r for r in chain.from_iterable(shrunk_regressions.values())]
    for regr in regressions:
        bisection_doc = _create_bisection(regr, db)
        if bisection_doc[models.BISECT_CHECKS_KEY]:
            utils.LOG.warn("Bisection already run: {} on {}".format(
                bisection_doc[models.TEST_CASE_PATH_KEY],
                bisection_doc[models.DEVICE_TYPE_KEY]
            ))
        else:
            _start_bisection(bisection_doc, jenkins_options)


def update_results(data, db_options=None):
    """Update test bisection results

    :param data: Meta-data of the test bisection including results
    :type data: dict
    :param db_options: The options for the database connection.
    :type db_options: dictionary
    :return A numeric value with the result status.
    """
    db = utils.db.get_db_connection(db_options)
    specs = {x: data[x] for x in [
        models.TYPE_KEY,
        models.ARCHITECTURE_KEY,
        models.DEFCONFIG_FULL_KEY,
        models.BUILD_ENVIRONMENT_KEY,
        models.JOB_KEY,
        models.KERNEL_KEY,
        models.GIT_BRANCH_KEY,
        models.LAB_NAME_KEY,
        models.DEVICE_TYPE_KEY,
        models.BISECT_GOOD_COMMIT_KEY,
        models.BISECT_BAD_COMMIT_KEY,
        models.TEST_CASE_PATH_KEY,
    ]}
    update = {k: data[k] for k in [
        models.BISECT_GOOD_SUMMARY_KEY,
        models.BISECT_BAD_SUMMARY_KEY,
        models.BISECT_FOUND_SUMMARY_KEY,
        models.BISECT_LOG_KEY,
        models.BISECT_CHECKS_KEY,
    ]}
    return utils.db.update(db[models.BISECT_COLLECTION], specs, update)
