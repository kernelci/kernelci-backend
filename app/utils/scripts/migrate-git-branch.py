#!/usr/bin/python
# Copyright (C) Linaro Limited 2017
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

"""Convert the defconfig_id fields into the new build_id one."""

import multiprocessing
import pymongo

import models
import utils
import utils.db


def log_error_update(collection, doc):
    utils.LOG.error(
        "Error updating '%s' document '%s'",
        collection, str(doc[models.ID_KEY]))


def log_error_add(collection, doc):
    utils.LOG.error(
        "Error adding git_branch key to '%s' document '%s'",
        collection, str(doc[models.ID_KEY]))


def get_db_connection():
    return pymongo.MongoClient()


def add_git_branch_field(collection_name):

    connection = get_db_connection()
    database = connection["kernel-ci"]

    def set_git_branch_field(doc, job_doc):
        ret_val = utils.db.update2(
            database,
            collection_name,
            {
                models.ID_KEY: doc[models.ID_KEY]
            },
            {
                "$set": {
                    models.GIT_BRANCH_KEY: job_doc[models.GIT_BRANCH_KEY]
                }
            }
        )

        if ret_val == 500:
            log_error_add(collection_name, doc)

    for doc in database[collection_name].find():
        if not doc.get(models.GIT_BRANCH_KEY):
            try:
                job_doc = utils.db.find_one2(
                    database[models.JOB_COLLECTION],
                    {models.ID_KEY: doc[models.JOB_ID_KEY]})

                set_git_branch_field(doc, job_doc)
            except KeyError:
                log_error_add(collection_name, doc)

    connection.close()


def convert_git_branch_field(collection_name):
    connection = get_db_connection()
    database = connection["kernel-ci"]

    for doc in database[collection_name].find():
        git_branch = doc.get(models.GIT_BRANCH_KEY)
        if git_branch and "local" in git_branch:
            ret_val = utils.db.update2(
                database,
                collection_name,
                {
                    models.ID_KEY: doc[models.ID_KEY]
                },
                {
                    "$set": {
                        models.GIT_BRANCH_KEY: git_branch
                    }
                })

            if ret_val == 500:
                log_error_update(collection_name, doc)

    connection.close()


if __name__ == "__main__":
    process_pool = multiprocessing.Pool(4)
    process_pool.map(
        convert_git_branch_field,
        [
            models.JOB_COLLECTION,
            models.BUILD_COLLECTION,
            models.ERROR_LOGS_COLLECTION,
        ]
    )

    process_pool.map(add_git_branch_field, [
        models.ERROR_LOGS_COLLECTION,
        models.ERRORS_SUMMARY_COLLECTION,
    ])

    process_pool.close()
    process_pool.join()
