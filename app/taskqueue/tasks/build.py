# Copyright (C) Collabora Limited 2017
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
#
# Copyright (C) Linaro Limited 2015,2016,2017
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

"""All build/job related celery tasks."""

import taskqueue.celery as taskc
import models
import utils.build
import utils.log_parser
import utils.logs.build


@taskc.app.task(name="import-build")
def import_build(json_obj):
    """Import a single build document.

    This is used to provide a Celery-task access to the import function.

    :param json_obj: The JSON object with the values necessary to import the
    build data.
    :type json_obj: dictionary
    :param db_options: The database connection options.
    :type db_options: dictionary
    :return The build ID, the job ID and whether this is the first build with
            this kernel revision being imported into the database.
    """
    db = utils.db.get_db_connection(taskc.app.conf.db_options)

    # There is a small window for a race condition here, if another build is
    # being imported between this request and when import_single_build() is
    # run.  A lock would solve it but with a cost, as builds would then not be
    # imported in parallel.  However it is benign to have duplicate revision
    # records in the data sent by kcidb, this test is merely to avoid sending
    # another record for _every_ build and limit the duplicates without
    # impacting performance.
    n_builds = db[models.BUILD_COLLECTION].count_documents(
        {models.KERNEL_KEY: json_obj['bmeta'][models.KERNEL_KEY]})
    first = (n_builds == 0)

    # build_id and job_id are necessary since they are injected by Celery into
    # another function.
    build_id, job_id, errors = utils.build.import_single_build(
        json_obj, taskc.app.conf.db_options)

    # TODO: handle errors.
    return build_id, job_id, first


@taskc.app.task(name="parse-single-build-log")
def parse_single_build_log(prev_res):
    """Wrapper around the real build log parsing function.

    Used to provided a task to the import function.

    :param prev_res: The results of the previous task, that should be a list
    with two elements: the build ID and the job ID.
    :type prev_res: list
    :param db_options: The database connection parameters.
    :type db_options: dictionary
    :return A 2-tuple: The status code, and the errors data structure.
    """
    status, errors = utils.log_parser.parse_single_build_log(
        prev_res[0], prev_res[1], taskc.app.conf.db_options)
    # TODO: handle errors.
    return status


@taskc.app.task(name="create-logs-summary")
def create_build_logs_summary(job, kernel, git_branch):
    """Task wrapper around the real function.

    Create the build logs summary.

    :param job: The tree value.
    :type job: str
    :param kernel: The kernel value.
    :type kernel: str
    :param git_branch: The branch name.
    :type git_branch: str
    """
    # TODO: handle error
    status, error = utils.logs.build.create_build_logs_summary(
        job, kernel, git_branch, taskc.app.conf.db_options)
    return status
