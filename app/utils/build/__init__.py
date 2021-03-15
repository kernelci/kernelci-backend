# Copyright (C) Collabora Limited 2017,2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: dcz-collabora <dorota.czaplejewicz@collabora.co.uk>
#
# Copyright (C) Linaro Limited 2015,2016,2017,2018,2019
# Author: Matt Hart <matthew.hart@linaro.org>
# Author: Milo Casagrande <milo.casagrande@linaro.org>
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

"""Functions to import builds/defconfigs."""

try:
    import simplejson as json
except ImportError:
    import json

try:
    from os import walk
except ImportError:
    from scandir import walk

import bson
import datetime
import io
import os
import pymongo.errors
import re
import redis
import types

import models
import models.build as mbuild
import models.job as mjob
import utils
import utils.database.redisdb as redisdb
import utils.db
import utils.errors

ERR_ADD = utils.errors.add_error
ERR_UPDATE = utils.errors.update_errors

# Regex to extract the kernel version.
# Should match strings that begins as:
# 4.1-1234-g12345
# 4.1.14-rc8-1234-g12345
# The 'rc*' pattern is part of the kernel version.
# TODO: add patches count extraction as well.
KERNEL_VERSION_MATCH = re.compile(r"^(?P<version>\d+\.{1}\d+(?:\.{1}\d+)?)")
KERNEL_RC_VERSION_MATCH = re.compile(
    r"^(?P<version>\d+\.{1}\d+(?:\.{1}\d+)?-{1}rc\d*)")


def _search_prev_build_doc(build_doc, database):
    """Search for a similar defconfig document in the database.

    Search for an already imported defconfig/build document in the database
    and return its object ID and creation date. This is done to make sure
    we do not create double documents when re-importing the same data or
    updating it.

    :param build_doc: The new defconfig document.
    :param database: The db connection.
    :return The previous doc ID and its creation date, or None.
    """
    doc_id = None
    c_date = None

    if build_doc and database:
        spec = {
            models.ARCHITECTURE_KEY: build_doc.arch,
            models.DEFCONFIG_FULL_KEY: build_doc.defconfig_full,
            models.DEFCONFIG_KEY: build_doc.defconfig,
            models.GIT_BRANCH_KEY: build_doc.git_branch,
            models.JOB_KEY: build_doc.job,
            models.KERNEL_KEY: build_doc.kernel,
            models.BUILD_ENVIRONMENT_KEY: build_doc.build_environment
        }
        collection = database[models.BUILD_COLLECTION]
        prev_doc_count = collection.count_documents(spec, limit=2)

        if prev_doc_count > 0:
            if prev_doc_count == 1:
                prev_doc = utils.db.find_one2(collection, spec)
                doc_id = prev_doc.get(models.ID_KEY)
                c_date = prev_doc.get(models.CREATED_KEY)
            else:
                utils.LOG.warn(
                    "Found multiple defconfig docs matching: {}".format(spec))
                utils.LOG.error(
                    "Cannot keep old document ID, don't know which one to "
                    "use!")

    return doc_id, c_date


class BuildError(Exception):
    def __init__(self, code, *args, **kwargs):
        self.code = code
        self.from_exc = kwargs.pop('from_exc', None)
        super(BuildError, self).__init__(*args, **kwargs)


def _update_job_doc(job_doc, job_id, status, build_doc, database):
    """Update the JobDocument with values from a BuildDocument.

    :param job_doc: The job document to update.
    :type job_doc: JobDocument
    :param status: The job status value.
    :type status: string
    :param build_doc: A BuildDocument object.
    :type build_doc: BuildDocument
    """
    to_update = False
    ret_val = 201

    if (job_id and job_doc.id != job_id):
        job_doc.id = job_id
        to_update = True

    if job_doc.status != status:
        job_doc.status = status
        to_update = True

    no_git = all([
        not job_doc.git_url,
        not job_doc.git_commit,
        not job_doc.git_describe,
        not job_doc.git_describe_v
    ])

    no_compiler = all([
        not job_doc.compiler,
        not job_doc.compiler_version,
        not job_doc.compiler_version_ext,
        not job_doc.compiler_version_full,
        not job_doc.cross_compile
    ])

    if (build_doc and no_git and no_compiler):
        # Kind of a hack:
        # We want to store some metadata at the job document level as well,
        # like git tree, git commit...
        # Since, at the moment, we do not have the metadata file at the job
        # level we need to pick one from the build documents, and extract some
        # values.
        if isinstance(build_doc, mbuild.BuildDocument):
            if (build_doc.job == job_doc.job and
                    build_doc.kernel == job_doc.kernel):
                job_doc.git_commit = build_doc.git_commit
                job_doc.git_describe = build_doc.git_describe
                job_doc.git_describe_v = build_doc.git_describe_v
                job_doc.kernel_version = build_doc.kernel_version
                job_doc.git_url = build_doc.git_url
                job_doc.compiler = build_doc.compiler
                job_doc.compiler_version = build_doc.compiler_version
                job_doc.compiler_version_ext = build_doc.compiler_version_ext
                job_doc.compiler_version_full = build_doc.compiler_version_full
                job_doc.cross_compile = build_doc.cross_compile
                to_update = True

    if to_update:
        ret_val, _ = utils.db.save(database, job_doc)
    return ret_val


def _get_or_create_job(meta, database, db_options):
    """Get or create a job in the database.

    :param job: The name of the job.
    :type job: str
    :param kernel: The name of the kernel.
    :type kernel: str
    :param database: The mongodb database connection.
    :param db_options: The database connection options.
    :type db_options: dict
    :return a 3-tuple: return value, job document and job ID.
    """
    ret_val = 201
    job_doc = None
    job_id = None

    rev = meta["bmeta"]["revision"]
    tree, descr, branch = (rev[key] for key in ["tree", "describe", "branch"])
    redis_conn = redisdb.get_db_connection(db_options)

    # We might be importing builds in parallel through multi-processes.  Keep a
    # lock here when looking for a job or we might end up with multiple job
    # creations.
    # ToDo: rename Job as Revision since that's what it really is
    lock_key = "build-import-{}-{}-{}".format(tree, descr, branch)
    with redis.lock.Lock(redis_conn, lock_key, timeout=5):
        p_doc = utils.db.find_one2(
            database[models.JOB_COLLECTION],
            {
                models.JOB_KEY: tree,
                models.KERNEL_KEY: descr,
                models.GIT_BRANCH_KEY: branch,
            })

        if p_doc:
            job_doc = mjob.JobDocument.from_json(p_doc)
            job_id = job_doc.id
        else:
            job_doc = mjob.JobDocument(tree, descr, branch)
            job_doc.status = models.BUILD_STATUS
            job_doc.created_on = datetime.datetime.now(tz=bson.tz_util.utc)
            ret_val, job_id = utils.db.save(database, job_doc)
            job_doc.id = job_id

    return ret_val, job_doc, job_id


def _get_build(meta, database):
    """Make a BuildDocument object and return it"""

    bmeta, steps, artifacts = (meta[key] for key in [
        "bmeta", "steps", "artifacts"
    ])
    env, kernel, rev, build = (bmeta[key] for key in [
        "environment", "kernel", "revision", "build"
    ])

    doc = mbuild.BuildDocument(
        rev["tree"],
        rev["describe"],
        kernel["defconfig"],
        rev["branch"],
        env["name"],
        defconfig_full=kernel["defconfig_full"]
    )

    # Required fields
    doc.arch = env["arch"]
    doc.git_commit = rev["commit"]
    doc.git_describe = rev["describe"]
    doc.status = build["status"]
    doc.git_url = rev["url"]
    doc.file_server_resource = kernel["publish_path"]
    doc.compiler_version_full = env["compiler_version_full"]
    doc.compiler_version_ext = doc.compiler_version_full  # ToDo: deprecate

    # Optional fields

    uname = env.get("platform", {}).get("uname")
    if uname and len(uname) == 6 and not uname[5]:
        uname[5] = steps[0]['cpus'].keys()[0]
    doc.build_platform = uname or []

    doc.build_time = build.get("duration")
    doc.compiler = env.get("compiler")
    doc.compiler_version = env.get("compiler_version")
    doc.cross_compile = env.get("cross_compile")
    doc.git_describe_v = rev.get("describe_verbose")
    doc.text_offset = kernel.get("text_offset")
    doc.vmlinux_bss_size = kernel.get("vmlinux_bss_size")
    doc.vmlinux_data_size = kernel.get("vmlinux_data_size")
    doc.vmlinux_file_size = kernel.get("vmlinux_file_size")
    doc.vmlinux_text_size = kernel.get("vmlinux_text_size")

    # Artifacts fields

    def _find_artifacts(artifacts, step, key=None, artifact_type=None):
        data = artifacts.get(step)
        found = list()
        if data:
            for entry in data:
                if key and entry.get("key") != key or \
                   artifact_type and entry.get("type") != artifact_type:
                    continue
                found.append(entry)
        return found

    kernel_config = _find_artifacts(artifacts, 'config', 'config')
    doc.kernel_config = kernel_config[0]['path'] if kernel_config else None

    doc.kconfig_fragments = [
        entry['path'] for entry in
        _find_artifacts(artifacts, 'config', 'fragment')
    ]

    kernel_images = _find_artifacts(artifacts, 'kernel', 'image')
    doc.kernel_image = kernel_images[0]['path'] if kernel_images else None

    system_map = _find_artifacts(artifacts, 'kernel', 'system_map')
    doc.system_map = system_map[0]['path'] if system_map else None

    modules = _find_artifacts(artifacts, 'modules', artifact_type='tarball')
    doc.modules = modules[0]['path'] if modules else None

    dtbs = _find_artifacts(artifacts, 'dtbs', artifact_type='directory')
    doc.dtb_dir = 'dtbs' if dtbs else None
    doc.dtb_dir_data = dtbs[0]['contents'] if dtbs else []

    # Build log
    log_artifacts = [
        _find_artifacts(artifacts, step, 'log')
        for step in ['kernel', 'modules']
    ]
    doc.kernel_build_logs = [log[0]['path'] for log in log_artifacts if log]
    doc.build_log = 'logs'
    doc.errors = 0
    doc.warnings = 0

    # Constant fields
    # FIXME: set in bmeta.json
    doc.version = "1.1"
    doc.build_type = "kernel"

    # Unused fields
    # FIXME: delete or make use of them if they're justified
    doc.file_server_url = None
    doc.kernel_image_size = None
    doc.modules_size = None
    doc.modules_dir = None
    doc.kernel_version = None

    return doc


def import_single_build(meta, db_options, base_path=utils.BASE_PATH):
    """Import a single build from the file system.

    :param json_obj: The json object containing the necessary data.
    :type json_obj: dictionary
    :param db_options: The database connection options.
    :type db_options: dictionary
    :param base_path: The base path on the file system where to look for.
    :type base_path: string
    :return The build id, job id and errors
    """
    build_id = None
    job_id = None

    database = utils.db.get_db_connection(db_options)

    ret_val, job_doc, job_id = _get_or_create_job(meta, database, db_options)

    if ret_val != 201:
        return None, None, {500: ["Failed to create job document"]}

    build_doc = _get_build(meta, database)
    build_doc.job_id = job_doc.id

    doc_id, c_date = _search_prev_build_doc(build_doc, database)
    build_doc.id = doc_id
    build_doc.created_on = c_date or datetime.datetime.now(tz=bson.tz_util.utc)

    ret_val = _update_job_doc(
        job_doc, job_id, job_doc.status, build_doc, database)
    if ret_val != 201:
        return None, None, {500: ["Failed to update job document"]}

    ret_val, build_id = utils.db.save(database, build_doc)
    if ret_val != 201:
        return None, None, {500: ["Failed to save build document"]}

    return build_id, job_id, {}
