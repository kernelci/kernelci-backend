# Copyright (C) Collabora Limited 2018
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

"""Common functions, variables for all kernelci utils modules."""

import bson
import os
import re

import models
import utils.log

BASE_PATH = "/var/www/images/kernel-ci"
LOG = utils.log.get_log()

# Build log file names.
BUILD_LOG_FILE = "logs/kernel.log"
BUILD_ERRORS_FILE = "logs/build-errors.log"
BUILD_WARNINGS_FILE = "logs/build-warnings.log"
BUILD_MISMATCHES_FILE = "logs/build-mismatches.log"

# All the mongodb ID keys we use.
ID_KEYS = [
    models.BUILD_ID_KEY,
    models.ID_KEY,
    models.JOB_ID_KEY,
    models.LAB_ID_KEY,
    models.TEST_CASE_ID_KEY,
    models.TEST_GROUP_ID_KEY
]

NO_START_CHARS = re.compile(r"^[^a-zA-Z0-9]")
NO_END_CHARS = re.compile(r"[^a-zA-Z0-9]$")
VALID_TEST_NAME = re.compile(r"[^a-zA-Z0-9\.\-_+]")
VALID_KCI_NAME = re.compile(r"[^a-zA-Z0-9\.\-_+=]")


def update_id_fields(spec):
    """Make sure ID fields are treated correctly.

    Update in-place ID fields to perform a search.

    If we search for an ID field, either _id or like job_id, that references
    a real _id in mongodb, we need to make sure they are treated as such.
    mongodb stores them as ObjectId elements.

    :param spec: The spec data structure with the parameters to check.
    :type spec: dict
    """
    if spec:
        common_keys = list(set(ID_KEYS) & set(spec.viewkeys()))
        for key in common_keys:
            try:
                spec[key] = bson.objectid.ObjectId(spec[key])
            except bson.errors.InvalidId, ex:
                # We remove the key since it won't serve anything good.
                utils.LOG.error(
                    "Wrong ID value for key '%s', got '%s': ignoring",
                    key, spec[key])
                utils.LOG.exception(ex)
                spec.pop(key, None)


def valid_name(name):
    """Check if a job or kernel name is valid.

    A valid name must start and end with an alphanumeric character, and must
    match the following regex:

    [a-zA-Z0-9.-_+=]+

    :param name: The name to test.
    :type name: str
    :return True or False.
    :rtype bool
    """
    is_valid = True
    if any([NO_START_CHARS.match(name),
            NO_END_CHARS.search(name), VALID_KCI_NAME.search(name)]):
        is_valid = False
    return is_valid


def valid_test_name(name):
    """Check if a test name is valid or not.

    A valid name must start and end with an alphanumeric character, and must
    match the following regex:

    [a-zA-Z0-9.-_+]+

    :param name: The name to test.
    :type name: str
    :return True or False.
    :rtype bool
    """
    is_valid = True
    if any([NO_START_CHARS.match(name),
            NO_END_CHARS.search(name), VALID_TEST_NAME.search(name)]):
        is_valid = False
    return is_valid


def is_hidden(value):
    """Verify if a file name or dir name is hidden (starts with .).

    :param value: The value to verify.
    :return True or False.
    """
    hidden = False
    if value.startswith("."):
        hidden = True
    return hidden


def is_lab_dir(value):
    """Verify if a file name or dir name is a lab one.

    A lab dir name starts with lab-.

    :param value: The value to verify.
    :return True or False.
    """
    is_lab = False
    if value.startswith("lab-"):
        is_lab = True
    return is_lab


# pylint: disable=invalid-name
def _extrapolate_defconfig_full_from_kconfig(kconfig_fragments, defconfig):
    """Try to extrapolate a valid value for the defconfig_full argument.

    When the kconfig_fragments filed is defined, it should have a default
    structure.

    :param kconfig_fragments: The config fragments value where to start.
    :type kconfig_fragments: str
    :param defconfig: The defconfig value to use. Will be returned if
    `kconfig_fragments` does not match the known ones.
    :type defconfig: str
    :return A string with the `defconfig_full` value or the provided
    `defconfig`.
    """
    defconfig_full = defconfig
    if (kconfig_fragments.startswith("frag-") and
            kconfig_fragments.endswith(".config")):

        defconfig_full = "%s+%s" % (
            defconfig,
            kconfig_fragments.replace("frag-", "").replace(".config", ""))
    return defconfig_full


def get_defconfig_full(
        build_dir, defconfig, defconfig_full, kconfig_fragments):
    """Get the value for defconfig_full variable based on available ones.

    :param build_dir: The directory we are parsing.
    :type build_dir: string
    :param defconfig: The value for defconfig.
    :type defconfig: string
    :param defconfig_full: The possible value for defconfig_full as taken from
    the build json file.
    :type defconfig_full: string
    :param kconfig_fragments: The config fragments value where to start.
    :type kconfig_fragments: string
    :return The defconfig_full value.
    """
    if (defconfig_full is None and kconfig_fragments is None):
        defconfig_full = defconfig
    elif (defconfig_full is None and kconfig_fragments is not None):
        # Infer the real defconfig used from the values we have.
        # Try first from the kconfig_fragments and then from the
        # directory we are traversing.
        defconfig_full_k = \
            _extrapolate_defconfig_full_from_kconfig(
                kconfig_fragments, defconfig)
        defconfig_full_d = os.path.basename(build_dir)

        # Default to use the one from kconfig_fragments.
        defconfig_full = defconfig_full_k
        # Use the one from the directory only if it is different from
        # the one obtained via the kconfig_fragments and if it is
        # different from the default defconfig value.
        if (defconfig_full_d is not None and
                defconfig_full_d != defconfig_full_k and
                defconfig_full_d != defconfig):
            defconfig_full = defconfig_full_k

    return defconfig_full
