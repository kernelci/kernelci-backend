# Copyright (C) Collabora Limited 2018,2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
#
# Copyright (C) Linaro Limited 2014,2015,2016,2017
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

"""Make sure indexes are created at startup."""

import pymongo

import models
import utils


INDEX_SPECS = {
    models.BISECT_COLLECTION: [
        [(models.NAME_KEY, pymongo.DESCENDING)],
        [(models.CREATED_KEY, pymongo.ASCENDING)],
    ],

    models.BUILD_COLLECTION: [
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
        ],
        [
            (models.JOB_KEY, pymongo.ASCENDING),
        ],
        [
            (models.KERNEL_KEY, pymongo.DESCENDING),
        ],
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.JOB_ID_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.GIT_COMMIT_KEY, pymongo.ASCENDING),
            (models.GIT_URL_KEY, pymongo.ASCENDING),
            (models.ID_KEY, pymongo.DESCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
        ],
        [
            (models.ARCHITECTURE_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_FULL_KEY, pymongo.ASCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.JOB_ID_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
        ],
        [
            (models.ARCHITECTURE_KEY, pymongo.ASCENDING),
            (models.BUILD_ENVIRONMENT_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_FULL_KEY, pymongo.ASCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
        ],
        [
            (models.ARCHITECTURE_KEY, pymongo.ASCENDING),
            (models.CREATED_KEY, pymongo.DESCENDING),
            (models.DEFCONFIG_FULL_KEY, pymongo.ASCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.ID_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
    ],

    models.DAILY_STATS_COLLECTION: [
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
        ]
    ],

    models.ERROR_LOGS_COLLECTION: [
        [
            (models.BUILD_ID_KEY, pymongo.DESCENDING),
        ],
    ],

    models.JOB_COLLECTION: [
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
        ],
        [
            (models.JOB_KEY, pymongo.ASCENDING),
        ],
        [
            (models.KERNEL_KEY, pymongo.ASCENDING),
        ],
    ],

    models.LAB_COLLECTION: [
        [
            (models.NAME_KEY, pymongo.ASCENDING),
            (models.TOKEN_KEY, pymongo.ASCENDING),
        ],
    ],

    models.REPORT_COLLECTION: [
        [
            (models.CREATED_KEY, pymongo.ASCENDING),
        ],
    ],

    models.TEST_CASE_COLLECTION: [
        [
            (models.TEST_GROUP_ID_KEY, pymongo.ASCENDING),
        ],
        [
            (models.MACH_KEY, pymongo.ASCENDING),
        ],
        [
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.NAME_KEY, pymongo.ASCENDING),
            (models.TEST_GROUP_ID_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
        ],
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.REGRESSION_ID_KEY, pymongo.ASCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
            (models.REGRESSION_ID_KEY, pymongo.ASCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.LAB_NAME_KEY, pymongo.ASCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.ARCHITECTURE_KEY, pymongo.ASCENDING),
            (models.BUILD_ENVIRONMENT_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_FULL_KEY, pymongo.ASCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.LAB_NAME_KEY, pymongo.ASCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
            (models.STATUS_KEY, pymongo.ASCENDING),
        ],
        [
            (models.ARCHITECTURE_KEY, pymongo.ASCENDING),
            (models.BUILD_ENVIRONMENT_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_FULL_KEY, pymongo.ASCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.LAB_NAME_KEY, pymongo.ASCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
        ],

    ],

    models.TEST_GROUP_COLLECTION: [
        [
            (models.CREATED_KEY, pymongo.DESCENDING),
            (models.PARENT_ID_KEY, pymongo.ASCENDING),
        ],
        [
            (models.BUILD_ID_KEY, pymongo.ASCENDING),
            (models.CREATED_KEY, pymongo.DESCENDING),
            (models.PARENT_ID_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.NAME_KEY, pymongo.ASCENDING),
            (models.PARENT_ID_KEY, pymongo.ASCENDING),
        ],
        [
            (models.DEVICE_TYPE_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.MACH_KEY, pymongo.ASCENDING),
            (models.NAME_KEY, pymongo.ASCENDING),
            (models.PARENT_ID_KEY, pymongo.ASCENDING),
        ],
        [
            (models.ARCHITECTURE_KEY, pymongo.ASCENDING),
            (models.BOARD_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_FULL_KEY, pymongo.ASCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.LAB_NAME_KEY, pymongo.ASCENDING),
            (models.NAME_KEY, pymongo.ASCENDING),
        ],
    ],

    models.TEST_REGRESSION_COLLECTION: [
        [
            (models.KERNEL_KEY, pymongo.DESCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.DESCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
        ],
        [
            (models.BUILD_ENVIRONMENT_KEY, pymongo.ASCENDING),
            (models.DEFCONFIG_FULL_KEY, pymongo.ASCENDING),
            (models.DEVICE_TYPE_KEY, pymongo.ASCENDING),
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
        ],
        [
            (models.GIT_BRANCH_KEY, pymongo.ASCENDING),
            (models.JOB_KEY, pymongo.ASCENDING),
            (models.KERNEL_KEY, pymongo.ASCENDING),
            (models.LAB_NAME_KEY, pymongo.ASCENDING),
            (models.PLAN_KEY, pymongo.ASCENDING),
        ],
    ],

    models.TOKEN_COLLECTION: [
        [
            (models.TOKEN_KEY, pymongo.DESCENDING),
        ],
    ],
}


INDEX_EXPIRATION = {
    (models.BISECT_COLLECTION, 'created_on_1'): 1209600,
    (models.REPORT_COLLECTION, 'created_on_1'): 604800,
}


def ensure_indexes(database):
    """Ensure that mongodb indexes exists, if not create them.

    This should be called at server startup.

    :param database: The database connection.
    """
    for collection, index_specs in INDEX_SPECS.iteritems():
        db_collection = database[collection]
        db_indexes = db_collection.index_information()

        for index in index_specs:
            name = '_'.join('_'.join(str(x) for x in spec) for spec in index)
            expire = INDEX_EXPIRATION.get((collection, name))
            if name not in db_indexes:
                kw = {'expireAfterSeconds': expire} if expire else {}
                db_collection.create_index(index, background=True, **kw)
