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


def _submit(data, bq_options):
    json_data = json.dumps(data, indent=2)
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
