# Copyright (C) Linaro Limited 2014,2015,2016,2017,2018
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

"""Celery configuration values."""

BROKER_URL = "redis://localhost/0"
BROKER_POOL_LIMIT = 250
BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 24000,
    "fanout_prefix": True,
    "fanout_patterns": True
}
CELERYD_PREFETCH_MULTIPLIER = 8
# Use custom json encoder.
CELERY_ACCEPT_CONTENT = ["kjson"]
CELERY_RESULT_SERIALIZER = "kjson"
CELERY_TASK_SERIALIZER = "kjson"
CELERY_TASK_RESULT_EXPIRES = 300
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_IGNORE_RESULT = False
CELERY_DISABLE_RATE_LIMITS = True
CELERY_RESULT_BACKEND = "redis://localhost/0"
CELERY_REDIS_MAX_CONNECTIONS = 250
# Custom log format.
CELERYD_LOG_FORMAT = '[%(levelname)8s/%(threadName)10s] %(message)s'
CELERYD_TASK_LOG_FORMAT = (
    '[%(levelname)8s/%(processName)10s] '
    '[%(task_name)s(%(task_id)s)] %(message)s'
)
# process 20 tasks per child before it's replaced
CELERYD_MAX_TASKS_PER_CHILD = 20
# kill the process if the task takes longer than 60 seconds
CELERYD_TASK_TIME_LIMIT = 90
