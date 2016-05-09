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

"""Handle upload of files to the storage system."""

import boto3
import io
import mimetypes
import multiprocessing.dummy as multiprocessing
import os

try:
    from scandir import walk
except ImportError:
    from os import walk

import utils


MIME_TYPES_BY_EXT = {
    ".dtb": "application/octet-stream",
    ".log": "text/plain",
    ".config": "text/plain",
    ".map": "text/plain"
}

MIME_TYPES_BY_NAME = {
    "vmlinux": "application/octet-stream",
    "zimage": "application/octet-stream"
}

NOT_TO_UPLOAD_FILES = [
    "vmlinux"
]


def upload_to_s3(path, aws_options):
    """Upload the provided path to S3.

    :param path: The path to the file to upload.
    :type path: str
    :param aws_options: The AWS S3 parameters.
    :type aws_options: dict
    :return A 2-tuple: status code, errors list.
    """
    ret_val = 500
    error = ""

    aws_session = boto3.session.Session(
        aws_access_key_id=aws_options["aws_access_key_id"],
        aws_secret_access_key=aws_options["aws_secret_access_key"]
    )
    s3_resource = aws_session.resource("s3")

    obj_key = path.replace(utils.BASE_PATH, "")
    if obj_key[0] == "/":
        obj_key = obj_key[1:]

    content_type = mimetypes.guess_type(path)[0]
    if not content_type:
        name, ext = os.path.splitext(os.path.split(path)[1])

        name = name.lower()
        ext = ext.lower()

        if ext in MIME_TYPES_BY_EXT.viewkeys():
            content_type = MIME_TYPES_BY_EXT[ext]
        elif name in MIME_TYPES_BY_NAME.viewkeys():
            content_type = MIME_TYPES_BY_NAME[name]
        else:
            content_type = "application/octet-stream"

    with io.open(path, mode="rb") as body:
        resp = \
            s3_resource.Object(aws_options["aws_s3_bucket"], obj_key).put(
                Body=body,
                ACL="public-read",
                CacheControl="public, no-transform",
                ContentType=content_type
                # TODO: expires?
            )
        utils.LOG.info(resp)
        ret_val = resp["ResponseMetadata"]["HTTPStatusCode"]
        if ret_val != 200:
            ret_val = 500

    return ret_val, error


def upload_build_artifacts(path, aws_options):
    """Scan the build directory and upload the artifacts found.

    :param path: The build directory to scan.
    :type path: str
    :param aws_options: The AWS connection parameters.
    :type aws_options: dict
    :return A 2-tuple: return value and errors list.
    """
    errors = []
    upload_status = []
    ret_val = 200

    def upload_callback(res):
        """Callback for the upload operation.

        :param res: The return value from the callee.
        :type res: tuple
        """
        upload_status.append(res[0])
        if res[1]:
            errors.append(res[1])

    def _scan_dir():
        """Recursively get file paths."""
        for root, _, files in walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                if all([file not in NOT_TO_UPLOAD_FILES,
                        os.path.isfile(file_path)]):
                    yield file_path

    if all([aws_options,
            aws_options.get("aws_access_key_id", None),
            aws_options.get("aws_secret_access_key", None),
            aws_options.get("aws_s3_bucket", None)]):

        if os.path.isdir(path):
            pool = multiprocessing.Pool(processes=10)

            for to_upload in _scan_dir():
                pool.apply_async(
                    upload_to_s3,
                    (to_upload, aws_options),
                    callback=upload_callback
                )

            pool.close()
            pool.join()

            ret_val = reduce(lambda x, y: x | y, upload_status)
        else:
            ret_val = 500
            errors.append("Provided directory to upload does not exists")
    else:
        ret_val = 500
        errors.append("Missing AWS credentials")

    if ret_val > 500:
        ret_val = 500

    return ret_val, errors
