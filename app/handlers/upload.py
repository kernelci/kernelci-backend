# Copyright (C) Linaro Limited 2015,2017
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

"""The RequestHandler for /upload URLs."""

import os
import tornado.web
import urlparse

import handlers.base as hbase
import handlers.common.token
import handlers.response as hresponse
import models
import utils.upload


class UploadHandler(hbase.BaseHandler):
    """Handler the /upload URLs."""

    def __init__(self, application, request, **kwargs):
        super(UploadHandler, self).__init__(application, request, **kwargs)

    @property
    def collection(self):
        return self.db[models.UPLOAD_COLLECTION]

    @staticmethod
    def _token_validation_func():
        return handlers.common.token.valid_token_upload

    @property
    def content_type(self):
        return "multipart/form-data"

    def execute_get(self, *args, **kwargs):
        """Execute the GET pre-operations.

        Checks that everything is OK to perform a GET.
        """
        response = None
        valid_token, _ = self.validate_req_token("GET")

        if valid_token:
            response = hresponse.HandlerResponse(501)
        else:
            response = hresponse.HandlerResponse(403)

        return response

    def execute_delete(self, *args, **kwargs):
        """Perform DELETE pre-operations.

        Check that the DELETE request is OK.
        """
        # TODO: in the future we need to enable delete as well.
        response = None
        valid_token, _ = self.validate_req_token("DELETE")

        if valid_token:
            response = hresponse.HandlerResponse(501)
        else:
            response = hresponse.HandlerResponse(403)

        return response

    def execute_post(self, *args, **kwargs):
        """Execute the POST pre-operations.

        Checks that everything is OK to perform a POST.
        """
        response = None
        valid_token, _ = self.validate_req_token("POST")

        if valid_token:
            valid_request = handlers.common.request.valid_post_request(
                self.request.headers,
                self.request.remote_ip, content_type=self.content_type)

            if valid_request == 200:
                path = self.get_argument("path", None)
                if path is None:
                    try:
                        job = self.get_argument(models.JOB_KEY)
                        branch = self.get_argument(models.GIT_BRANCH_KEY)
                        kernel = self.get_argument(models.KERNEL_KEY)
                        defconfig = self.get_argument(models.DEFCONFIG_KEY)
                        defconfig_full = self.get_argument(
                            models.DEFCONFIG_FULL, defconfig)
                        arch = self.get_argument(models.ARCHITECTURE_KEY)
                        lab = self.get_argument(models.LAB_NAME_KEY, None)

                        path = os.path.join(
                            job, branch, kernel, arch, defconfig_full)
                        if lab is not None:
                            path = os.path.join(path, lab)
                    except tornado.web.MissingArgumentError as ex:
                        self.log.exception(ex)
                        response = hresponse.HandlerResponse(
                            ex.status_code)
                        response.reason = ex.log_message

                if path:
                    if not path.endswith("/"):
                        path += "/"
                    if path.startswith("/"):
                        path = path[1:]

                    if utils.upload.is_valid_dir_path(path):
                        ret_val, reason = \
                            utils.upload.check_or_create_upload_dir(path)
                        if ret_val == 200:
                            response = self._save_files(path)
                        else:
                            response = hresponse.HandlerResponse(ret_val)
                            response.reason = reason
                    else:
                        response = hresponse.HandlerResponse(400)
                        response.reason = "Provided path is not a directory"
            else:
                response = hresponse.HandlerResponse(valid_request)
                response.reason = (
                    "%s: %s" %
                    (
                        self._get_status_message(valid_request),
                        "Use %s as the content type" % self.content_type
                    )
                )
        else:
            response = hresponse.HandlerResponse(403)

        return response

    def _put(self, *args, **kwargs):
        response = hresponse.HandlerResponse(201)

        path = kwargs.get("path", None)
        if path:
            # Path points to a file, treat it like that.
            if path[-1] == "/":
                path = path[:-1]
            if path[0] == "/":
                path = path[1:]

            filename = os.path.basename(path)
            dir_path = os.path.dirname(path)

            if utils.upload.is_valid_dir_path(dir_path):
                ret_val, error = \
                    utils.upload.check_or_create_upload_dir(dir_path)

                if ret_val == 200:
                    prev_file = utils.upload.file_exists(path)

                    ret_dict = utils.upload.create_or_update_file(
                        dir_path, filename, None, self.request.body)

                    if ret_dict["status"] == 200 or ret_dict["status"] == 201:
                        if prev_file:
                            response.status_code = 200
                            response.reason = (
                                "File '%s' replaced with new content" %
                                filename)
                        else:
                            response.reason = "File '%s' saved" % filename
                            location = self._create_storage_url(path)
                            if location is not None:
                                response.headers = {"Location": location}
                    else:
                        response.status_code = ret_dict["status"]
                        response.reason = "Unable to save file"

                    response.result = [ret_dict]
                else:
                    response.status_code = ret_val
                    response.reason = error
            else:
                response.status_code = 500
                response.reason = (
                    "Cannot save file at the provided '%s' destination" % path)
        else:
            response.status_code = 400
            response.reason = "Missing destination path"

        return response

    def _create_storage_url(self, path):
        """Create the new storage location for the uploaded file.

        :param path: The path of the file.
        :type path: str
        :return The new storage URL.
        """
        storage_url = self.settings["storage_url"]
        new_storage_url = None

        if storage_url:
            split_url = urlparse.urlsplit(storage_url)
            new_storage_url = urlparse.urlunsplit(
                (
                    split_url.scheme, split_url.netloc, path, split_url.query,
                    split_url.fragment
                )
            )

        return new_storage_url

    def _save_files(self, path):
        """Parse the request and for each file, save it.

        :param path: The directory path where to save the files.
        :type str
        :return A `HandlerResponse` object.
        """
        response = hresponse.HandlerResponse()

        if self.request.files:
            response.result = [
                utils.upload.create_or_update_file(
                    path,
                    u_file[0]["filename"],
                    u_file[0]["content_type"],
                    u_file[0]["body"]
                )
                for u_file in self.request.files.itervalues()
            ]
        else:
            response.status_code = 400
            response.reason = "No files provided"

        return response
