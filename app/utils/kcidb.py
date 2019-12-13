# Copyright (C) Collabora Limited 2019
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

"""Push data using kcidb-submit."""

import json
import os
import subprocess

import models
import utils
import utils.db
from utils.report.common import DEFAULT_STORAGE_URL as STORAGE_URL

# Mapping between kcidb revision keys and build documents
BUILD_REV_KEY_MAP = {
    'git_repository_url': models.GIT_URL_KEY,
    'git_repository_commit_hash': models.GIT_COMMIT_KEY,
    'git_repository_commit_name': models.GIT_DESCRIBE_V_KEY,
    'git_repository_branch': models.GIT_BRANCH_KEY,
}


def _make_id(raw_id, ns):
    return ':'.join([ns, str(raw_id)])


def _get_build_doc(group, db):
    keys = [
        models.JOB_KEY,
        models.KERNEL_KEY,
        models.GIT_BRANCH_KEY,
        models.ARCHITECTURE_KEY,
        models.DEFCONFIG_KEY,
        models.BUILD_ENVIRONMENT_KEY,
    ]
    spec = {k: group[k] for k in keys}

    return utils.db.find_one2(db[models.BUILD_COLLECTION], spec)


def _get_test_cases(group, db, hierarchy, ns):
    case_collection = db[models.TEST_CASE_COLLECTION]
    group_collection = db[models.TEST_GROUP_COLLECTION]

    hierarchy = hierarchy + [group[models.NAME_KEY]]
    tests = [
        {
            'id': _make_id(test[models.ID_KEY], ns),
            'path': '.'.join(hierarchy + [test[models.NAME_KEY]]),
            'status': test[models.STATUS_KEY],
            # ToDo: get start and duration times from LAVA log timestamps
            'start_time': test[models.CREATED_KEY].isoformat(),
        }
        for test in (
            utils.db.find_one2(case_collection, test_id)
            for test_id in group[models.TEST_CASES_KEY]
        )
    ]

    for sub_group_id in group[models.SUB_GROUPS_KEY]:
        sub_group = utils.db.find_one2(group_collection, sub_group_id)
        tests += _get_test_cases(sub_group, db, hierarchy, ns)

    return tests


def _submit(data, bq_options):
    json_data = json.dumps(data, indent=2)
    if bq_options.get("debug"):
        utils.LOG.info("Submitting with kcidb:")
        utils.LOG.info(json_data)
    local_env = dict(os.environ)
    local_env["GOOGLE_APPLICATION_CREDENTIALS"] = bq_options["credentials"]
    kcidb_path = bq_options.get("kcidb_path", "")
    kcidb_submit = os.path.join(kcidb_path, "kcidb-submit")
    p = subprocess.Popen([kcidb_submit, "-d", bq_options["dataset"]],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         env=local_env)
    p.communicate(input=json_data)
    if p.returncode:
        utils.LOG.warn("Failed to push data to BigQuery")


def push_build(build_id, first, bq_options, db_options={}, db=None):
    if db is None:
        db = utils.db.get_db_connection(db_options)
    origin = bq_options.get("origin", "kernelci")
    ns = bq_options.get("namespace", "kernelci.org")
    build = utils.db.find_one2(db[models.BUILD_COLLECTION], build_id)
    build_id = _make_id(build[models.ID_KEY], ns)
    revision_id = _make_id(build[models.KERNEL_KEY], ns)

    bq_data = {
        'version': '1',
    }

    if first:
        bq_revision = {
            'origin': origin,
            'origin_id': revision_id,
        }
        bq_revision.update({
            bq_key: build[build_key]
            for bq_key, build_key in BUILD_REV_KEY_MAP.iteritems()
        })
        bq_data['revisions'] = [bq_revision]

    bq_build = {
        'revision_origin': origin,
        'revision_origin_id': revision_id,
        'origin': origin,
        'origin_id': build_id,
        'valid': build[models.STATUS_KEY] == 'PASS',
        'start_time': build[models.CREATED_KEY].isoformat(),
        'description': build[models.GIT_DESCRIBE_V_KEY],
        'duration': build[models.BUILD_TIME_KEY],
        'architecture': build[models.ARCHITECTURE_KEY],
        'compiler': build[models.COMPILER_VERSION_FULL_KEY],
        'log_url': '/'.join([
            STORAGE_URL,
            build[models.FILE_SERVER_RESOURCE_KEY],
            utils.BUILD_LOG_FILE
        ]),
        'misc': {
            'defconfig': build[models.DEFCONFIG_FULL_KEY],
        },
    }
    bq_data['builds'] = [bq_build]

    _submit(bq_data, bq_options)


def push_tests(group_id, bq_options, db_options={}, db=None):
    if db is None:
        db = utils.db.get_db_connection(db_options)
    collection = db[models.TEST_GROUP_COLLECTION]
    group = utils.db.find_one2(collection, group_id)
    origin = bq_options.get("origin", "kernelci")
    ns = bq_options.get("namespace", "kernelci.org")
    test_cases = _get_test_cases(group, db, [], ns)
    build = _get_build_doc(group, db)
    if not build:
        utils.LOG.warn("kcidb: Missing build, unable to push tests.")
        return
    build_id = _make_id(build[models.ID_KEY], ns)
    env_description = "{} in {}".format(
        group[models.DEVICE_TYPE_KEY],
        group[models.LAB_NAME_KEY]
    )
    test_description = "{} on {} in {}".format(
        group[models.NAME_KEY],
        group[models.DEVICE_TYPE_KEY],
        group[models.LAB_NAME_KEY]
    )
    misc = {
        'plan': group[models.NAME_KEY],
        'plan_variant': group[models.PLAN_VARIANT_KEY],
    }
    env_misc = {
        'device': group[models.DEVICE_TYPE_KEY],
        'lab': group[models.LAB_NAME_KEY],
        'mach': group[models.MACH_KEY],
        'rootfs_url': group[models.INITRD_KEY],
        'instance': group[models.BOARD_INSTANCE_KEY],
    }

    files = {
        'txt': group[models.BOOT_LOG_KEY],
        'html': group[models.BOOT_LOG_HTML_KEY],
        'lava_json': 'lava-{}.json'.format(group[models.DEVICE_TYPE_KEY]),
    }

    output_files = []
    for name, file in files.iteritems():
        url = "/".join([
            STORAGE_URL,
            build[models.FILE_SERVER_RESOURCE_KEY],
            group[models.LAB_NAME_KEY],
            file])
        output_files.append({"name": name, "url": url})

    bq_data = {
        'version': '1',
        "tests": [
            {
                'build_origin': origin,
                'build_origin_id': build_id,
                'origin': origin,
                'origin_id': test['id'],
                'environment': {
                    'description': env_description,
                    'misc': env_misc,
                },
                'path': test['path'],
                'description': test_description,
                'status': test['status'],
                'start_time': test['start_time'],
                'output_files': output_files,
                'misc': misc,
            }
            for test in test_cases
        ],
    }
    _submit(bq_data, bq_options)
