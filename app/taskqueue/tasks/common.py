# Copyright (C) Linaro Limited 2015
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

"""General use celery tasks or functions."""

from __future__ import absolute_import

import celery

import taskqueue.celery as taskc
import utils.batch.common


@taskc.app.task(name="batch-executor", ignore_result=False)
def execute_batch(json_obj, db_options):
    """Run batch operations based on the passed JSON object.

    :param json_obj: The JSON object with the operations to perform.
    :type json_obj: dict
    :param db_options: The database connection parameters.
    :type db_options: dict
    :return The result of the batch operations.
    """
    return utils.batch.common.execute_batch_operation(json_obj, db_options)


@taskc.app.task(name="batch-serial-executor", ignore_result=False)
def execute_batch_serial(batch_op_list, db_options):
    """Run list of batch operations in series.

    :param json_obj: List of JSON object with the operations to perform.
    :type json_obj: list
    :param db_options: The database connection parameters.
    :type db_options: dict
    :return A list with the results of each batch operation.
    """
    return [
        utils.batch.common.execute_batch_operation(batch_op, db_options)
        for batch_op in batch_op_list
    ]


def run_batch_group(batch_op_list, db_options):
    """Execute a list of batch operations.

    :param batch_op_list: List of JSON object used to build the batch
    operation.
    :type batch_op_list: list
    :param db_options: The database connection parameters.
    :type db_options: dict
    :return A list with all the results.
    """
    job = celery.group(
        execute_batch.s(batch_op, db_options)
        for batch_op in batch_op_list
    )
    result = job.apply_async()
    while not result.ready():
        pass
    # Use the result backend optimezed function to retrieve the results.
    # We are using redis.
    return result.join_native()
