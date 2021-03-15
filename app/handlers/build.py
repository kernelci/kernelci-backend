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

"""The RequestHandler for /build URLs."""

import celery
import jsonschema
import handlers.base as hbase
import handlers.response as hresponse
import models
import taskqueue.tasks
import taskqueue.tasks.kcidb
import taskqueue.tasks.build as taskq
import utils.db


STEPS_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["PASS", "FAIL"],
            },
        },
        "required": ["name", "status"],
    },
}

ARTIFACTS_SCHEMA = {
    "type": "object",
    "patternProperties": {
        ".*": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["file", "directory", "tarball"],
                    },
                    "path": {"type": "string"},
                    "key": {"type": "string"},
                    "contents": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["type", "path"],
            },
        },
    },
    "required": ["kernel"],
}

BMETA_SCHEMA = {
    "type": "object",
    "properties": {
        "build": {
            "type": "object",
            "properties": {
                "duration": {"type": "number", "minimum": 0},
                "status": {
                    "type": "string",
                    "enum": ["PASS", "FAIL"],
                },
            },
            "required": ["status"],
        },
        "environment": {
            "type": "object",
            "properties": {
                "arch": {"type": "string"},
                "name": {"type": "string"},
                "compiler_version_full": {"type": "string"},
            },
            "required": ["name", "arch", "compiler_version_full"],
        },
        "kernel": {
            "type": "object",
            "properties": {
                "defconfig": {"type": "string"},
                "defconfig_full": {"type": "string"},
                "publish_path": {"type": "string"},
            },
            "required": ["defconfig", "defconfig_full", "publish_path"],
        },
        "revision": {
            "type": "object",
            "properties": {
                "branch": {"type": "string"},
                "commit": {
                    "type": "string",
                    "pattern": "^[0-9a-f]+$",
                    "minLength": 40,
                    "maxLength": 40,
                },
                "describe": {"type": "string"},
                "describe_verbose": {"type": "string"},
                "tree": {"type": "string"},
                "url": {"type": "string"},
            },
            "required": ["branch", "commit", "describe", "tree", "url"],
        },
    },
    "required": [
        "build", "environment", "kernel", "revision"
    ],
}

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://kernelci.org/build.schema.json",
    "title": "KernelCI Build",
    "description": "A kernel build",
    "type": "object",
    "properties": {
        "bmeta": BMETA_SCHEMA,
        "steps": STEPS_SCHEMA,
        "artifacts": ARTIFACTS_SCHEMA,
    },
    "required": [
        "bmeta", "steps", "artifacts"
    ],
}


class BuildHandler(hbase.BaseHandler):
    """Handle the /build URLs."""

    def __init__(self, application, request, **kwargs):
        super(BuildHandler, self).__init__(application, request, **kwargs)

    @property
    def collection(self):
        return self.db[models.BUILD_COLLECTION]

    @staticmethod
    def _valid_keys(method):
        return models.BUILD_VALID_KEYS.get(method, None)

    def is_valid_json(self, json_obj, **kwargs):
        res, error = True, ""
        try:
            jsonschema.validate(instance=json_obj, schema=SCHEMA)
        except jsonschema.ValidationError as ex:
            self.log.exception(ex)
            error = str(ex)
            res = False
        return res, error

    def _post(self, *args, **kwargs):
        response = hresponse.HandlerResponse(202)
        response.reason = "Request accepted and being imported"

        tasks = [
            taskq.import_build.s(kwargs["json_obj"]),
            taskqueue.tasks.kcidb.push_build.s(),
            taskq.parse_single_build_log.s(),
        ]
        celery.chain(tasks).apply_async(
            link_error=taskqueue.tasks.error_handler.s())

        return response
