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

"""All build/job related celery tasks."""

import os

from celery import chord

import models
import taskqueue.celery as taskc
import utils
import utils.build
import utils.log_parser
import utils.storage


@taskc.app.task(name="import-job")
def import_job(json_obj, db_options, mail_options=None):
    """Just a wrapper around the real import function.

    This is used to provide a Celery-task access to the import function.

    :param json_obj: The JSON object with the values necessary to import the
    job.
    :type json_obj: dictionary
    :param db_options: The database connection parameters.
    :type db_options: dictionary
    :param mail_options: The options necessary to connect to the SMTP server.
    :type mail_options: dictionary
    :return The ID of the job document.
    """
    # job_id is necessary since it is injected by Celery into another function.
    job_id, errors = utils.build.import_multiple_builds(json_obj, db_options)
    # TODO: handle errors.
    return job_id


@taskc.app.task(name="import-build")
def import_build(json_obj):
    """Import a single build document.

    This is used to provide a Celery-task access to the import function.

    :param json_obj: The JSON object with the values necessary to import the
    build data.
    :type json_obj: dictionary
    :return The build ID and the job ID.
    """
    # build_id and job_id are necessary since they are injected by Celery into
    # another function.
    build_id, job_id, errors = utils.build.import_single_build(
        json_obj, taskc.app.conf["DB_OPTIONS"])
    # TODO: handle errors.
    return build_id, job_id


@taskc.app.task(name="parse-build-log")
def parse_build_log(prev_res):
    """Wrapper around the real build log parsing function.

    Used to provided a task to the import function.

    :param prev_res: The results of the previous task, that should be a list
    with two elements: the build ID and the job ID.
    :type prev_res: list
    :return A 2-tuple: The status code, and the errors data structure.
    """
    status, errors = utils.log_parser.parse_single_build_log(
        prev_res[0], prev_res[1], taskc.app.conf["DB_OPTIONS"])
    # TODO: handle errors.
    return status, prev_res[0]


@taskc.app.task(name="upload-artifacts")
def upload_artifacts(prev_res, json_obj):
    """Upload build artifacts to the file storage.

    :param prev_res: The results from the previous task.
    :type prev_res: list
    :param json_obj: The JSON data as sent by the client.
    :type json_obj: dict
    :return The status code.
    """
    j_get = json_obj.get
    job_dir = os.path.join(utils.BASE_PATH, j_get(models.JOB_KEY))
    kernel_dir = os.path.join(job_dir, j_get(models.KERNEL_KEY))

    build_rel_dir = "{:s}-{:s}".format(
        j_get(models.ARCHITECTURE_KEY),
        j_get(models.DEFCONFIG_FULL_KEY, None) or j_get(models.DEFCONFIG_KEY)
    )
    build_dir = os.path.join(kernel_dir, build_rel_dir)

    ret_val, errors = utils.storage.upload_build_artifacts(
        build_dir, taskc.app.conf["AWS_OPTIONS"])

    # TODO: handle errors
    return ret_val


@taskc.app.task(name="remove-local-artifacts")
def remove_local_artifacts(prev, json_obj):
    """Remove the local artifacts from the filesystem.

    :param prev_res: The results from the previous task.
    :type prev_res: list
    :param json_obj: The JSON data as sent by the client.
    :type json_obj: dict
    """
    # TODO
    return 200


def complete_build_import(json_obj):
    """Complete the build import.

    Wrapper around the real tasks execution.

    Parse the JSON file, parse the build logs, upload data to the storage
    server, and then delete the local data.

    :param json_obj: The JSON data as sent by the client.
    :type json_obj: dict
    """
    chord(
        header=(import_build.s(json_obj) | parse_build_log.s() |
                upload_artifacts.s(json_obj))
    )(remove_local_artifacts.s(json_obj))
