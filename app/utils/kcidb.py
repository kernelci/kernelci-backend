# Copyright (C) Collabora Limited 2019, 2020
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
import threading
import urlparse

import models
import utils
import utils.db
from utils.report.common import DEFAULT_STORAGE_URL as STORAGE_URL


class KcidbSubmit(object):
    def __init__(self, kcidb_options):
        kcidb_path = kcidb_options.get("kcidb_path", "")
        self.kcidb_submit_cmd = os.path.join(kcidb_path, "kcidb-submit")
        self.project = kcidb_options["project"]
        self.topic = kcidb_options["topic"]
        self.credentials = kcidb_options["credentials"]
        self.debug = kcidb_options.get("debug")
        self._process = None
        self._lock = threading.Lock()

    @property
    def process(self):
        if not self._process:
            self._process = self._spawn()
        return self._process

    def _spawn(self):
        local_env = dict(os.environ)
        local_env["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials
        self._lock.acquire()
        process = subprocess.Popen([self.kcidb_submit_cmd,
                                    "-p", self.project,
                                    "-t", self.topic],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   env=local_env)
        self._lock.release()
        return process

    def terminate(self):
        if self._process:
            self.process.communicate()
        elif self.debug:
            utils.LOG.info("No kcidb-submit process running")

    def write(self, json_data):
        self.process.stdin.write(json_data)
        if not json_data.endswith('\n'):
            self.process.stdin.write('\n')
        self.process.stdin.flush()
        if self.process.returncode:
            utils.LOG.warn("Failed to push data to KCIDB")


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


def _submit(data, kcidb_options, kcidb_submit):
    json_data = json.dumps(data, indent=2)
    if kcidb_options.get("debug"):
        utils.LOG.info("Submitting with kcidb:")
        utils.LOG.info(json_data)
    kcidb_submit.write(json_data)


def push_build(build_id, first, kcidb_options, kcidb_submit,
               db_options={}, db=None):
    if db is None:
        db = utils.db.get_db_connection(db_options)
    origin = kcidb_options.get("origin", "kernelci")
    ns = kcidb_options.get("namespace", "kernelci.org")
    build = utils.db.find_one2(db[models.BUILD_COLLECTION], build_id)
    build_id = _make_id(build[models.ID_KEY], ns)
    revision_id = build[models.GIT_COMMIT_KEY]

    kcidb_data = {
        'version': '1',
    }

    if first:
        kcidb_revision = {
            'origin': origin,
            'origin_id': revision_id,
            'valid': True,
            'discovery_time': build[models.CREATED_KEY].isoformat(),
        }
        kcidb_revision.update({
            kcidb_key: build[build_key]
            for kcidb_key, build_key in BUILD_REV_KEY_MAP.iteritems()
        })
        kcidb_data['revisions'] = [kcidb_revision]

    files = {
        'kernel_image': build[models.KERNEL_IMAGE_KEY],
        'modules': build[models.MODULES_KEY],
        'System.map': build[models.SYSTEM_MAP_KEY],
    }
    output_files = []
    for name, file in files.iteritems():
        if file:
            url = "/".join([
                STORAGE_URL,
                build[models.FILE_SERVER_RESOURCE_KEY],
                file])
            output_files.append({"name": name, "url": url})

    kcidb_build = {
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
        'log_url': urlparse.urljoin(
            STORAGE_URL,
            '/'.join([
                build[models.FILE_SERVER_RESOURCE_KEY],
                build[models.BUILD_LOG_KEY],
            ])
        ),
        'config_name': build[models.DEFCONFIG_FULL_KEY],
        'config_url': urlparse.urljoin(
            STORAGE_URL,
            '/'.join([
                build[models.FILE_SERVER_RESOURCE_KEY],
                build[models.KERNEL_CONFIG_KEY],
            ])
        ),
        'output_files': output_files,
        'misc': {
            'kernel_image_size': build[models.KERNEL_IMAGE_SIZE_KEY],
            'vmlinux_bss_size': build[models.VMLINUX_BSS_SIZE_KEY],
            'vmlinux_data_size': build[models.VMLINUX_DATA_SIZE_KEY],
            'build_platform': build[models.BUILD_PLATFORM_KEY],
        },
    }
    kcidb_data['builds'] = [kcidb_build]
    _submit(kcidb_data, kcidb_options, kcidb_submit)


def _get_test_misc(group, test):
    misc = {
        'plan': group[models.NAME_KEY],
        'plan_variant': group[models.PLAN_VARIANT_KEY],
        'kernelci_status': test['status']
    }
    return misc


def push_tests(group_id, kcidb_options, kcidb_submit,
               db_options={}, db=None):
    status_translate = {
        'UNKNOWN': 'SKIP'
    }
    if db is None:
        db = utils.db.get_db_connection(db_options)
    collection = db[models.TEST_GROUP_COLLECTION]
    group = utils.db.find_one2(collection, group_id)
    origin = kcidb_options.get("origin", "kernelci")
    ns = kcidb_options.get("namespace", "kernelci.org")
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
        url = urlparse.urljoin(
            STORAGE_URL,
            '/'.join([
                build[models.FILE_SERVER_RESOURCE_KEY],
                group[models.LAB_NAME_KEY],
                file,
            ])
        )
        output_files.append({"name": name, "url": url})

    kcidb_data = {
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
                'status': status_translate.get(test['status'], test['status']),
                'waived': False,
                'start_time': test['start_time'],
                'output_files': output_files,
                'misc': _get_test_misc(group, test)
            }
            for test in test_cases
        ],
    }
    _submit(kcidb_data, kcidb_options, kcidb_submit)
