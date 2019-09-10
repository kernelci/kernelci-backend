# Copyright (C) Linaro Limited 2015,2016,2018
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

"""Model and fields for the delta/comparison."""

import models


JOB_DELTA_COMPARE_TO_VALID_KEYS = [
    models.JOB_ID_KEY,
    models.JOB_KEY,
    models.KERNEL_KEY
]

JOB_DELTA_VALID_KEYS = {
    "POST": [
        models.COMPARE_TO_KEY,
        models.JOB_ID_KEY,
        models.JOB_KEY,
        models.KERNEL_KEY
    ]
}

BUILD_DELTA_VALID_KEYS = {
    "POST": [
        models.ARCHITECTURE_KEY,
        models.BUILD_ID_KEY,
        models.COMPARE_TO_KEY,
        models.DEFCONFIG_FULL_KEY,
        models.DEFCONFIG_KEY,
        models.JOB_KEY,
        models.KERNEL_KEY,
        models.BUILD_ENVIRONMENT_KEY
    ]
}

BOOT_DELTA_VALID_KEYS = {
    "POST": [
        models.ARCHITECTURE_KEY,
        models.BOARD_KEY,
        models.BOOT_ID_KEY,
        models.COMPARE_TO_KEY,
        models.DEFCONFIG_FULL_KEY,
        models.DEFCONFIG_KEY,
        models.JOB_KEY,
        models.KERNEL_KEY,
        models.LAB_NAME_KEY
    ]
}

BUILD_COMPARE_TO_VALID_KEYS = [
    models.ARCHITECTURE_KEY,
    models.BUILD_ID_KEY,
    models.DEFCONFIG_FULL_KEY,
    models.DEFCONFIG_KEY,
    models.JOB_KEY,
    models.KERNEL_KEY,
    models.BUILD_ENVIRONMENT_KEY
]

BOOT_COMPARE_VALID_KEYS = [
    models.ARCHITECTURE_KEY,
    models.BOARD_KEY,
    models.BOOT_ID_KEY,
    models.DEFCONFIG_FULL_KEY,
    models.DEFCONFIG_KEY,
    models.JOB_KEY,
    models.KERNEL_KEY,
    models.LAB_NAME_KEY
]

COMPARE_VALID_KEYS = {
    models.BOOT_COLLECTION: BOOT_DELTA_VALID_KEYS,
    models.BUILD_COLLECTION: BUILD_DELTA_VALID_KEYS,
    models.JOB_COLLECTION: JOB_DELTA_VALID_KEYS
}

# Matching between compare resources and their real database collection.
# This is used for GET operations.
COMPARE_RESOURCE_COLLECTIONS = {
    models.BOOT_COLLECTION: models.BOOT_DELTA_COLLECTION,
    models.BUILD_COLLECTION: models.BUILD_DELTA_COLLECTION,
    models.JOB_COLLECTION: models.JOB_DELTA_COLLECTION
}
