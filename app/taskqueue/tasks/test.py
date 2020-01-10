# Copyright (C) Collabora Limited 2017, 2018, 2019, 2020
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
#
# Copyright (C) Baylibre 2017
# Author: lollivier <lollivier@baylibre.com>
#
# Copyright (C) Linaro Limited 2015,2016
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

"""All test related celery tasks."""

import taskqueue.celery as taskc
import utils
import utils.kci_test.regressions


@taskc.app.task(name="test-regressions")
def find_regression(group_id):
    """Find test case regressions in the given test group.

    Run this function in a Celery task to find any test case regressions for
    the given test group document ID, recursively through all sub-groups.

    :param group_id: Test group document object ID.
    :return tuple 200 if OK, 500 in case of errors; a list with created test
    regression document ids
    """
    return utils.kci_test.regressions.find(group_id, taskc.app.conf.db_options)
