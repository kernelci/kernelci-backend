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

"""All storage upload and local delete related operations."""

import os

try:
    from scandir import walk
except ImportError:
    from os import walk

from celery import chord

import models
import taskqueue.celery as taskc
import utils
import utils.storage
import utils.upload


@taskc.app.task(name="remove-build-artifacts")
def remove_build_artifacts(prev_res, json_obj):
    """Remove the local artifacts from the filesystem.

    This is a special case for the build artifacts.

    :param prev_res: The results from the previous task.
    :type prev_res: list
    :param json_obj: The JSON data as sent by the client.
    :type json_obj: dict
    """
    def _scan_dir(path):
        for root, _, files in walk(path):
            for file in files:
                yield os.path.join(root, file)

    if prev_res[0] == 200:
        build_dir = utils.create_build_dir(json_obj)

        for to_del in _scan_dir(build_dir):
            try:
                os.remove(to_del)
            except OSError as ex:
                if ex.errno != 2:
                    # TODO: handle errors
                    utils.LOG.error(
                        "Error removing file '%s': %s", to_del, ex.errno)


@taskc.app.task(name="remove-single-artifact")
def remove_single_artifact(prev_res, path):
    """Remove a single artifact from the filesystem

    :param prev_res: The results from the previous task.
    :type prev_res: list
    :param path: The path to the artifact to remove.
    :type path: str
    """
    if prev_res[0][0] == 200:
        try:
            os.remove(utils.upload.check_upload_path(path))
        except OSError as ex:
            # OSError is 2 when the file is not found.
            if ex.errno != 2:
                # TODO: handle errors
                utils.LOG.error("Error removing file '%s': %s", path, ex.errno)


@taskc.app.task(name="upload-single-artifact")
def upload_single_artifact(path):
    """Upload a single artifact to the storage system.

    :param path: The path to the artifact to upload.
    :type path: str
    """
    return utils.storage.upload_artifact(
        utils.upload.check_upload_path(path), taskc.app.conf["AWS_OPTIONS"])


@taskc.app.task(name="build-upload-artifacts")
def upload_build_artifacts(prev_res, json_obj):
    """Upload build artifacts to the file storage.

    :param prev_res: The results from the previous task.
    :type prev_res: list
    :param json_obj: The JSON data as sent by the client.
    :type json_obj: dict
    :return The status code.
    """
    build_dir = utils.create_build_dir(json_obj)
    ret_val, errors = utils.storage.upload_build_artifacts(
        build_dir, taskc.app.conf["AWS_OPTIONS"])

    # TODO: handle errors
    return ret_val


@taskc.app.task(name="complete-boot-import")
def complete_boot_import(prev_res, json_obj):
    """Complete the boot import uploading, and deleting, the boot JSON report.

    :param prev_res: The results from the previous task.
    :type prev_res: list
    :param json_obj: The JSON data as sent by the client.
    :type json_obj: dict
    """
    boot_dir = utils.create_boot_dir(json_obj)
    path = os.path.join(
        boot_dir,
        utils.BOOT_REPORT_FORMAT.format(json_obj.get(models.BOARD_KEY)))

    utils.LOG.info("BOOT PATH: %s", path)

    chord(
        header=upload_single_artifact.s(path)
    )(remove_single_artifact.s(path))


def complete_single_import(path):
    """Wrapper around the single artifact import task.

    Upload the artifact to the file storage system, and then delete it
    from the local filesystem.

    :param path: The path to the artifact to upload and remove.
    :type path: str
    """
    chord(
        header=upload_single_artifact.s(path)
    )(remove_single_artifact.s(path))
