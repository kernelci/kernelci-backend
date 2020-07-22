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

"""Calculate statistics."""

import bson
import datetime
import itertools
import pymongo

import models
import models.stats as mstats
import utils
import utils.db


# These are used to create the document attributes as in the model.
OLD_PREFIXES = ["daily", "weekly", "biweekly"]


def calculate_job_stats(database, date_range):
    """Calculate statistics for the job collection.

    :param database: The database connection.
    :param date_range: The list of date ranges to calculate statistics for.
    :param date_range: list
    :return A dictionary containing the job statistics.
    """
    utils.LOG.info("Calculating job statistics")
    job_collection = database[models.JOB_COLLECTION]

    job_stats = {
        "total_jobs": job_collection.count(),
        "total_unique_trees": len(job_collection.distinct(models.JOB_KEY)),
        "total_unique_kernels": len(job_collection.distinct(models.KERNEL_KEY))
    }

    for idx, date in enumerate(date_range):
        prefix = OLD_PREFIXES[idx]

        job_data = job_collection.find({models.CREATED_KEY: {"$lt": date}})

        job_stats[prefix + "_total_jobs"] = job_data.count()
        job_stats[prefix + "_unique_trees"] = \
            len(job_data.distinct(models.JOB_KEY))
        job_stats[prefix + "_unique_kernels"] = \
            len(job_data.distinct(models.KERNEL_KEY))

    return job_stats


def calculate_build_stats(database, date_range):
    """Calculate statistics for the build collection.

    :param database: The database connection.
    :param date_range: The list of date ranges to calculate statistics for.
    :param date_range: list
    :return A dictionary containing the build statistics.
    """
    utils.LOG.info("Calculating build statistics")
    build_collection = database[models.BUILD_COLLECTION]

    build_stats = {
        "total_builds": build_collection.count(),
        "total_unique_defconfigs": len(
            build_collection.distinct(models.DEFCONFIG_KEY))
    }

    for idx, date in enumerate(date_range):
        prefix = OLD_PREFIXES[idx]

        build_data = build_collection.find(
            {models.CREATED_KEY: {"$lt": date}})

        build_stats[prefix + "_total_builds"] = build_data.count()
        build_stats[prefix + "_unique_defconfigs"] = \
            len(build_data.distinct(models.DEFCONFIG_KEY))

    return build_stats


def get_start_date(database):
    """Retrieve the date of the first object stored in the database.

    :param database: The database connection.
    :return The date of the first document stored or None.
    """
    utils.LOG.info("Retrieving start date")

    start_date = None
    spec = {
        models.CREATED_KEY: {"$ne": None}
    }
    sort = [(models.CREATED_KEY, pymongo.ASCENDING)]
    fields = [models.CREATED_KEY]

    start_doc = utils.db.find(
        database[models.JOB_COLLECTION],
        1, 0, spec=spec, fields=fields, sort=sort)

    if start_doc:
        start_date = start_doc[0][models.CREATED_KEY]

    return start_date


def iter_dicts(dict0, dict1):
    """Iterate through 3 dictionaries at once.

    :param dict0: A dictionary to iterate through.
    :type dict0: dict
    :param dict1: A dictionary to iterate through.
    :type dict1: dict
    :return Yield the key-value pairs from each dictionaries, returning None
    to fill empty values.
    """
    for item0, item1 in itertools.izip_longest(
            dict0.iteritems(), dict1.iteritems()):
        yield item0
        yield item1


def calculate_daily_stats(db_options):
    """Calculate statistics.

    :param db_options: The database connection parameters.
    :type db_options: dict
    :return A DailyStats object.
    """
    database = utils.db.get_db_connection(db_options)

    today = datetime.datetime.now(tz=bson.tz_util.utc)
    yesterday = today - datetime.timedelta(days=1)
    one_week = today - datetime.timedelta(days=7)
    two_weeks = today - datetime.timedelta(days=14)

    date_range = [yesterday, one_week, two_weeks]

    start_date = get_start_date(database)
    job_stats = calculate_job_stats(database, date_range)
    build_stats = calculate_build_stats(database, date_range)

    daily_stats = mstats.DailyStats()
    daily_stats.start_date = start_date
    for item in iter_dicts(job_stats, build_stats):
        if item:
            setattr(daily_stats, item[0], item[1])

    return daily_stats
