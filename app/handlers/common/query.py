# Copyright (C) Linaro Limited 2015,2016,2017
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

"""Handlers functions to work on query args."""

import bson
import datetime
import pymongo
import types

import models
import utils

# Default value to calculate a date range in case the provided value is
# out of range.
DEFAULT_DATE_RANGE = 5

# Default value to calculate a time range in case the provided one is not
# valid.
DEFAULT_TIME_RANGE = 60
# Maximum time range possible, otherwise use a date_range value.
MAX_TIME_RANGE = 60 * 24
MIN_TIME_RANGE = 10

# Some key values must be treated in a different way, not as string.
KEY_TYPES = {
    models.RETRIES_KEY: "int",
    models.WARNINGS_KEY: "int"
}

MIDNIGHT = datetime.time(tzinfo=bson.tz_util.utc)
ALMOST_MIDNIGHT = datetime.time(23, 59, 59, tzinfo=bson.tz_util.utc)
EPOCH = datetime.datetime(1970, 1, 1, tzinfo=bson.tz_util.utc)


def _valid_value(value):
    """Make sure the passed value is valid for its type.

    This is necessary when value passed are like 0, False or similar and
    are actually valid values.

    :return True or False.
    """
    valid_value = True
    if isinstance(value, types.StringTypes):
        if value == "":
            valid_value = False
    elif isinstance(value, (types.ListType, types.TupleType)):
        if not value:
            valid_value = False
    elif value is None:
        valid_value = False
    return valid_value


def get_and_add_gte_lt_keys(spec, query_args_func, valid_keys):
    """Get the gte and lt query args values and add them to the spec.

    This is necessary to perform searches like 'greater than-equal' and
    'less-than'.

    :param spec: The spec data structure where to add the elements.
    :type spec: dict
    :param query_args_func: A function used to return a list of the query
    arguments.
    :type query_args_func: function
    :param valid_keys: The valid keys for this request.
    :type valid_keys: list
    """
    gte = query_args_func(models.GTE_KEY)
    less = query_args_func(models.LT_KEY)
    spec_get = spec.get

    if gte and isinstance(gte, types.ListType):
        for arg in gte:
            _parse_and_add_gte_lt_value(
                arg, "$gte", valid_keys, spec, spec_get)
    elif gte and isinstance(gte, types.StringTypes):
        _parse_and_add_gte_lt_value(gte, "$gte", valid_keys, spec, spec_get)

    if less and isinstance(less, types.ListType):
        for arg in less:
            _parse_and_add_gte_lt_value(arg, "$lt", valid_keys, spec, spec_get)
    elif less and isinstance(less, types.StringTypes):
        _parse_and_add_gte_lt_value(less, "$lt", valid_keys, spec, spec_get)


def _parse_and_add_gte_lt_value(
        arg, operator, valid_keys, spec, spec_get_func=None):
    """Parse and add the provided query argument.

    Parse the argument looking for its value, and in case we have a valid value
    add it to the `spec` data structure.

    :param arg: The argument as retrieved from the request.
    :type arg: str
    :param operator: The operator to use, either '$gte' or '$lt'.
    :type operator: str
    :param valid_keys: The valid keys that this request can accept.
    :type valid_keys: list
    :param spec: The `spec` data structure where to store field-value.
    :type spec: dict
    :param spec_get_func: Optional get function of the spec data structure used
    to retrieve values from it.
    :type spec_get_func: function
    """
    field = value = None
    try:
        field, value = arg.split(",")
        if field not in valid_keys:
            field = None
            utils.LOG.warn(
                "Wrong field specified for '%s', got '%s'",
                operator, field)

        val_type = KEY_TYPES.get(field, None)
        if val_type and val_type == "int":
            try:
                value = int(value)
            except ValueError, ex:
                utils.LOG.error(
                    "Error converting value to %s: %s",
                    val_type, value)
                utils.LOG.exception(ex)
                value = None

        if field is not None and _valid_value(value):
            _add_gte_lt_value(
                field, value, operator, spec, spec_get_func)
    except ValueError, ex:
        error_msg = (
            "Wrong value specified for '%s' query argument: %s" %
            (operator, arg)
        )
        utils.LOG.error(error_msg)
        utils.LOG.exception(ex)


def _add_gte_lt_value(field, value, operator, spec, spec_get_func=None):
    """Add the field-value pair to the spec data structure.

    :param field: The field name.
    :type field: str
    :param value: The value of the field.
    :type value: str
    :param operator: The operator to use, either '$gte' or '$lt'.
    :type operator: str
    :param spec: The `spec` data structure where to store field-value.
    :type spec: dict
    :param spec_get_func: Optional get function of the spec data structure used
    to retrieve values from it.
    :type spec_get_func: function
    """
    if not spec_get_func:
        spec_get_func = spec.get

    prev_val = spec_get_func(field, None)
    new_key_val = {operator: value}

    if prev_val:
        prev_val.update(new_key_val)
    else:
        spec[field] = new_key_val


def get_aggregate_value(query_args_func):
    """Get the value of the aggregate key.

    :param query_args_func: A function used to return a list of the query
    arguments.
    :type query_args_func: function
    :return The aggregate value as string.
    """
    aggregate = query_args_func(models.AGGREGATE_KEY)
    if not aggregate:
        aggregate = None
    return aggregate


def get_query_spec(query_args_func, valid_keys):
    """Get values from the query string to build a `spec` data structure.

    A `spec` data structure is a dictionary whose keys are the keys
    accepted by this handler method.

    :param query_args_func: A function used to return a list of the query
    arguments.
    :type query_args_func: function
    :param valid_keys: A list containing the valid keys that should be
    retrieved.
    :type valid_keys: list
    :return A `spec` data structure (dictionary).
    """
    def _get_spec_values():
        """Get the values for the spec data structure.

        Internally used only, with some logic to differentiate between single
        and multiple values. Makes sure also that the list of values is valid,
        meaning that we do not have None or empty values.

        :return A tuple with the key and its value.
        """
        val_type = None

        for key in valid_keys:
            val_type = KEY_TYPES.get(key, None)
            val = query_args_func(key) or []
            if val:
                # Go through the values and make sure we have valid ones.
                val = [v for v in val if _valid_value(v)]
                len_val = len(val)

                if len_val == 1:
                    if val_type and val_type == "int":
                        try:
                            val = int(val[0])
                        except ValueError, ex:
                            utils.LOG.error(
                                "Error converting value to %s: %s",
                                val_type, val[0])
                            utils.LOG.exception(ex)
                            val = []
                    else:
                        val = val[0]
                elif len_val > 1:
                    # More than one value, make sure we look for all of them.
                    if val_type and val_type == "int":
                        try:
                            val = {"$in": [int(v) for v in val]}
                        except ValueError, ex:
                            utils.LOG.error(
                                "Error converting list of values to %s: %s",
                                val_type, val)
                            utils.LOG.exception(ex)
                            val = []
                    else:
                        val = {"$in": val}

            yield key, val

    spec = {}
    if valid_keys and isinstance(valid_keys, types.ListType):
        spec = {
            k: None if v == 'null' else v
            for (k, v) in _get_spec_values() if _valid_value(v)
        }

    return spec


def get_created_on_date(query_args_func):
    """Retrieve the `created_on` key from the query args.

    :param query_args_func: A function used to return a list of query
    arguments.
    :type query_args_func: function
    :return A `datetime.date` object or None.
    """
    created_on = query_args_func(models.CREATED_KEY)
    valid_date = None

    if created_on:
        if isinstance(created_on, types.ListType):
            created_on = created_on[-1]

        if isinstance(created_on, types.StringTypes):
            tries = 3
            while tries > 0:
                tries -= 1
                try:
                    valid_date = datetime.datetime.strptime(
                        created_on, "%Y-%m-%d")
                except AttributeError:
                    # XXX: For some reasons, sometimes we get an exception here
                    # saying: module object does not have attribute _strptime.
                    utils.LOG.warn("Retrying valid date calculation")
                    continue
                except ValueError:
                    try:
                        valid_date = datetime.datetime.strptime(
                            created_on, "%Y%m%d")
                    except ValueError:
                        utils.LOG.error(
                            "No valid value provided for '%s' key, got '%s'",
                            models.CREATED_KEY, created_on)
                    finally:
                        break
                else:
                    break
            if valid_date:
                valid_date = datetime.date(
                    valid_date.year, valid_date.month, valid_date.day)

    return valid_date


def add_created_on_date(spec, created_on):
    """Add the `created_on` key to the search spec data structure.

    :param spec: The dictionary where to store the key-value.
    :type spec: dictionary
    :param created_on: The `date` as passed in the query args.
    :type created_on: `datetime.date`
    :return The passed `spec` updated.
    """
    if created_on and isinstance(created_on, datetime.date):
        start_date = datetime.datetime.combine(created_on, MIDNIGHT)
        end_date = datetime.datetime.combine(created_on, ALMOST_MIDNIGHT)

        spec[models.CREATED_KEY] = {
            "$gte": start_date, "$lt": end_date}
    else:
        # Remove the key if, by chance, it got into the spec with
        # previous iterations on the query args.
        if models.CREATED_KEY in spec.viewkeys():
            spec.pop(models.CREATED_KEY, None)

    return spec


def get_and_add_date_range(spec, query_args_func, created_on=None):
    """Retrieve the `date_range` query from the request.

    Add the retrieved `date_range` value into the provided `spec` data
    structure.

    :param spec: The dictionary where to store the key-value.
    :type spec: dictionary
    :param query_args_func: A function used to return a list of query
    arguments.
    :type query_args_func: function
    :param created_on: The `date` as passed in the query args.
    :type created_on: `datetime.date`
    :return The passed `spec` updated.
    """
    date_range = query_args_func(models.DATE_RANGE_KEY)

    if date_range:
        # Start date needs to be set at the end of the day!
        if created_on and isinstance(created_on, datetime.date):
            # If the created_on key is defined, along with the date_range one
            # we combine the both and calculate a date_range from the provided
            # values. created_on must be a `date` object.
            today = datetime.datetime.combine(created_on, ALMOST_MIDNIGHT)
        else:
            today = datetime.datetime.combine(
                datetime.date.today(), ALMOST_MIDNIGHT)

        previous = calculate_date_range(date_range, created_on)

        spec[models.CREATED_KEY] = {"$gte": previous, "$lt": today}
    return spec


def get_and_add_time_range(spec, query_args_func):
    """Retrieve the `time_range` query from the request.

    Add the retrieved `time_range` value into the provided `spec` data
    structure.

    :param spec: The dictionary where to store the key-value.
    :type spec: dictionary
    :param query_args_func: A function used to return a list of query
    arguments.
    :type query_args_func: function
    :return The passed `spec` updated.
    """
    time_range = query_args_func(models.TIME_RANGE_KEY)

    if time_range:
        if isinstance(time_range, types.ListType):
            time_range = time_range[-1]

        if isinstance(time_range, types.StringTypes):
            try:
                time_range = int(time_range)
            except ValueError:
                # TODO: report error
                utils.LOG.error(
                    "Wrong value passed to time_range: %s", time_range)
                time_range = DEFAULT_TIME_RANGE

        time_range = abs(time_range)
        if time_range > MAX_TIME_RANGE:
            time_range = MAX_TIME_RANGE
        if time_range < MIN_TIME_RANGE:
            time_range = MIN_TIME_RANGE

        delta = datetime.timedelta(minutes=time_range)
        now = datetime.datetime.now(tz=bson.tz_util.utc)
        spec[models.CREATED_KEY] = {"$lt": now, "$gte": now - delta}

    return spec


def calculate_date_range(date_range, created_on=None):
    """Calculate the new date subtracting the passed number of days.

    It removes the passed days from today date, calculated at midnight
    UTC.

    :param date_range: The number of days to remove from today.
    :type date_range int, long, str
    :return A new `datetime.date` object that is the result of the
    subtraction of `datetime.date.today()` and
    `datetime.timedelta(days=date_range)`.
    """
    if isinstance(date_range, types.ListType):
        date_range = date_range[-1]

    if isinstance(date_range, types.StringTypes):
        try:
            date_range = int(date_range)
        except ValueError:
            utils.LOG.error(
                "Wrong value passed to date_range: %s", date_range)
            date_range = DEFAULT_DATE_RANGE

    date_range = abs(date_range)
    if date_range > datetime.timedelta.max.days:
        date_range = DEFAULT_DATE_RANGE

    # Calcuate with midnight in mind though, so we get the starting of
    # the day for the previous date.
    if created_on and isinstance(created_on, datetime.date):
        today = datetime.datetime.combine(created_on, MIDNIGHT)
    else:
        today = datetime.datetime.combine(datetime.date.today(), MIDNIGHT)
    delta = datetime.timedelta(days=date_range)

    return today - delta


def get_query_fields(query_args_func):
    """Get values from the query string to build a `fields` data structure.

    A `fields` data structure can be either a list or a dictionary.

    :param query_args_func: A function used to return a list of query
    arguments.
    :type query_args_func: function
    :return A `fields` data structure (list or dictionary).
    """
    fields = None
    y_fields, n_fields = map(
        query_args_func, [models.FIELD_KEY, models.NOT_FIELD_KEY])

    if y_fields and not n_fields:
        fields = list(set(y_fields))
    elif n_fields:
        fields = dict.fromkeys(list(set(y_fields)), True)
        fields.update(dict.fromkeys(list(set(n_fields)), False))

    return fields


def get_query_sort(query_args_func):
    """Get values from the query string to build a `sort` data structure.

    A `sort` data structure is a list of tuples in a `key-value` fashion.
    The keys are the values passed as the `sort` argument on the query,
    they values are based on the `sort_order` argument and defaults to the
    descending order.

    :param query_args_func: A function used to return a list of query
    arguments.
    :type query_args_func: function
    :return A `sort` data structure, or None.
    """
    sort = None
    sort_fields, sort_order = map(
        query_args_func, [models.SORT_KEY, models.SORT_ORDER_KEY])

    if sort_fields:
        if sort_order and isinstance(sort_order, types.ListType):
            sort_order = int(sort_order[-1])
        else:
            sort_order = pymongo.DESCENDING

        # Wrong number for sort order? Force descending.
        if (sort_order != pymongo.ASCENDING and
                sort_order != pymongo.DESCENDING):
            utils.LOG.warn(
                "Wrong sort order used (%d), default to %d",
                sort_order, pymongo.DESCENDING
            )
            sort_order = pymongo.DESCENDING

        sort = [
            (field, sort_order)
            for field in sort_fields
        ]

    return sort


def get_skip_and_limit(query_args_func):
    """Retrieve the `skip` and `limit` query arguments.

    :param query_args_func: A function used to return a list of query
    arguments.
    :type query_args_func: function
    :return A tuple with the `skip` and `limit` arguments.
    """
    skip, limit = map(query_args_func, [models.SKIP_KEY, models.LIMIT_KEY])

    if skip and isinstance(skip, types.ListType):
        skip = int(skip[-1])
    else:
        skip = 0

    if limit and isinstance(limit, types.ListType):
        limit = int(limit[-1])
    else:
        limit = 0

    return skip, limit


def get_values(query_args_func, valid_keys):
    spec = get_query_spec(query_args_func, valid_keys)

    created_on = get_created_on_date(query_args_func)
    add_created_on_date(spec, created_on)

    get_and_add_date_range(spec, query_args_func, created_on)
    get_and_add_gte_lt_keys(spec, query_args_func, valid_keys)
    get_and_add_time_range(spec, query_args_func)
    utils.update_id_fields(spec)

    # First the spec.
    yield spec
    # Then the sort.
    yield get_query_sort(query_args_func)
    # Then the actual fields.
    yield get_query_fields(query_args_func)
    # Then the skip value.
    skip, limit = get_skip_and_limit(query_args_func)
    yield skip
    yield limit
    # Then the aggregate values.
    yield get_aggregate_value(query_args_func)


def get_all_query_values(query_args_func, valid_keys):
    """Handy function to get all query args in a batch.

    :param query_args_func: A function used to return a list of the query
    arguments.
    :type query_args_func: function
    :param valid_keys: A list containing the valid keys that should be
    retrieved.
    :type valid_keys: list
    :return A 6-tuple
    """
    return (val for val in get_values(query_args_func, valid_keys))
