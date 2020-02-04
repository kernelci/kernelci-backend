.. _collection_job:

job
---

More info about the job schema can be found :ref:`here <schema_job>`.

.. note::

    This resource can also be accessed using the plural form ``jobs``.

GET
***

.. http:get:: /job/(string:id)/

 Get all the available jobs or a single one if ``id`` is provided.

 :param id: The :ref:`ID <intro_schema_ids>` of the job to retrieve.
 :type id: string

 :reqheader Authorization: The token necessary to authorize the request.
 :reqheader Accept-Encoding: Accept the ``gzip`` coding.

 :resheader Content-Type: Will be ``application/json; charset=UTF-8``.

 :query int limit: Number of results to return. Default 0 (all results).
 :query int skip: Number of results to skip. Default 0 (none).
 :query string sort: Field to sort the results on. Can be repeated multiple times.
 :query int sort_order: The sort order of the results: -1 (descending), 1
    (ascending). This will be applied only to the first ``sort``
    parameter passed. Defaults to -1.
 :query int date_range: Number of days to consider, starting from today
    (:ref:`more info <intro_schema_time_date>`). By default consider all results.
 :query string field: The field that should be returned in the response. Can be
    repeated multiple times.
 :query string nfield: The field that should *not* be returned in the response. Can be repeated multiple times.
 :query string _id: The internal ID of the job report.
 :query string created_on: The creation date: accepted formats are ``YYYY-MM-DD`` and ``YYYYMMDD``.
 :query string job: A job name.
 :query string kernel: A kernel name.
 :query string status: The status of the job report.
 :query string time_range: Minutes of data to consider, in UTC time
    (:ref:`more info <intro_schema_time_date>`). Minimum value is 10 minutes, maximum
    is 60 * 24.

 :status 200: Results found.
 :status 403: Not authorized to perform the operation.
 :status 404: The provided resource has not been found.
 :status 500: Internal server error.
 :status 503: Service maintenance.

 **Example Requests**

 .. sourcecode:: http

    GET /job/012345678901234567890123/ HTTP/1.1
    Host: api.kernelci.org
    Accept: */*
    Authorization: token

 .. sourcecode:: http

    GET /job?date_range=12&job=arm-soc&field=status&field=kernel HTTP/1.1
    Host: api.kernelci.org
    Accept: */*
    Authorization: token

 **Example Responses**

 .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept-Encoding
    Date: Mon, 11 Aug 2014 15:12:50 GMT
    Content-Type: application/json; charset=UTF-8

    {
        "code": 200,
        "count:" 261,
        "limit": 0,
        "result": [
            {
                "status": "PASS",
                "job": "arm-soc",
                "_id": "012345678901234567890123",
            },
        ],
    }

 .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept-Encoding
    Date: Mon, 11 Aug 2014 15:23:00 GMT
    Content-Type: application/json; charset=UTF-8

    {
        "code": "200",
        "result": [
            {
                "status": "PASS",
                "job": "next",
                "_id": "0123456789001234567890123",
                "kernel": "next-20140731"
            }
        ]
    }

 .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept-Encoding
    Date: Mon, 11 Aug 2014 15:23:00 GMT
    Content-Type: application/json; charset=UTF-8

    {
        "code": 200,
        "count": 4,
        "limit": 0,
        "result": [
            {
                "status": "PASS",
                "kernel": "v3.16-rc6-1009-g709032a"
            },
            {
                "status": "PASS",
                "kernel": "v3.16-rc6-1014-g716519f"
            }
        ]
    }

 .. note::
    Results shown here do not include the full JSON response.

.. http:get:: /job/distinct/(string:field)

 Get all the unique values for the specified ``field``.
 Accepted ``field`` values are:

 * `compiler_version_ext`
 * `compiler_version`
 * `compiler`
 * `git_branch`
 * `git_commit`
 * `git_describe_v`
 * `git_describe`
 * `git_url`
 * `job`
 * `kernel_version`
 * `kernel`

 The query parameters can be used to first filter the data on which the unique
 value should be retrieved.

 :param field: The name of the field to get the unique values of.
 :type field: string

 :reqheader Authorization: The token necessary to authorize the request.
 :reqheader Accept-Encoding: Accept the ``gzip`` coding.

 :resheader Content-Type: Will be ``application/json; charset=UTF-8``.

 :query int limit: Number of results to return. Default 0 (all results).
 :query int skip: Number of results to skip. Default 0 (none).
 :query string sort: Field to sort the results on. Can be repeated multiple times.
 :query int sort_order: The sort order of the results: -1 (descending), 1
    (ascending). This will be applied only to the first ``sort``
    parameter passed. Default -1.
 :query int date_range: Number of days to consider, starting from today
    (:ref:`more info <intro_schema_time_date>`). By default consider all results.
 :query string field: The field that should be returned in the response. Can be
    repeated multiple times.
 :query string nfield: The field that should *not* be returned in the response. Can be repeated multiple times.
 :query string _id: The internal ID of the job report.
 :query string created_on: The creation date: accepted formats are ``YYYY-MM-DD`` and ``YYYYMMDD``.
 :query string job: A job name.
 :query string kernel: A kernel name.
 :query string status: The status of the job report.

 :status 200: Results found.
 :status 400: Wrong ``field`` value provided.
 :status 403: Not authorized to perform the operation.
 :status 404: The provided resource has not been found.
 :status 500: Internal server error.
 :status 503: Service maintenance.

 **Example Requests**

 .. sourcecode:: http

    GET /job/distinct/job HTTP/1.1
    Host: api.kernelci.org
    Accept: */*
    Authorization: token

 .. sourcecode:: http

    GET /job/distinct/kernel?job=next&date_range=5 HTTP/1.1
    Host: api.kernelci.org
    Accept: */*
    Authorization: token

 **Example Responses**

 .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept-Encoding
    Date: Mon, 11 Aug 2014 15:12:50 GMT
    Content-Type: application/json; charset=UTF-8

    {
        "code": 200,
        "count:" 49,
        "result": [
            "next",
            "mainline",
            "omap"
        ]
    }

 .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept-Encoding
    Date: Mon, 11 Aug 2014 15:23:00 GMT
    Content-Type: application/json; charset=UTF-8

    {
        "code": 200,
        "count": 3,
        "result": [
            "next-20150826",
            "next-20150825",
            "next-20150824"
        ]
    }

 .. note::
    Results shown here do not include the full JSON response.

.. http:get:: /job/(string:id)/logs
.. http:get:: /job/logs

 Get the summary of the logs of the builds associated with the job.

 For more info about the available fields, see the :ref:`build logs summary schema <schema_build_logs_summary>`.

 :param id: The ID of the job.
 :type id: string

 :reqheader Authorization: The token necessary to authorize the request.
 :reqheader Accept-Encoding: Accept the ``gzip`` coding.

 :resheader Content-Type: Will be ``application/json; charset=UTF-8``.

 :query int limit: Number of results to return. Default 0 (all results).
 :query int skip: Number of results to skip. Default 0 (none).
 :query string sort: Field to sort the results on. Can be repeated multiple times.
 :query int sort_order: The sort order of the results: -1 (descending), 1
    (ascending). This will be applied only to the first ``sort``
    parameter passed. Default -1.
 :query int date_range: Number of days to consider, starting from today
    (:ref:`more info <intro_schema_time_date>`). By default consider all results.
 :query string field: The field that should be returned in the response. Can be
    repeated multiple times.
 :query string nfield: The field that should *not* be returned in the response. Can be repeated multiple times.
 :query string created_on: The creation date: accepted formats are ``YYYY-MM-DD`` and ``YYYYMMDD``.
 :query string job: The name of a job.
 :query string job_id: The ID of a job.
 :query string kernel: The name of a kernel.

 :status 200: Results found.
 :status 400: Wrong ``id`` value provided.
 :status 403: Not authorized to perform the operation.
 :status 404: The provided resource has not been found.
 :status 500: Internal server error.
 :status 503: Service maintenance.

 **Example Requests**

 .. sourcecode:: http

    GET /job/123456789012345678901234/logs HTTP/1.1
    Host: api.kernelci.org
    Accept: */*
    Authorization: token

 **Example Responses**

 .. sourcecode:: http

    HTTP/1.1 200 OK
    Vary: Accept-Encoding
    Date: Wed, 2 Sept 2015 11:12:50 GMT
    Content-Type: application/json; charset=UTF-8

    {
        "code": 200,
        "result": [
            {
                "_id": {
                    "$oid": "123456789012345678901234"
                },
                "job_id": {
                    "$oid": "123456789012345678901234"
                },
                "job": "next",
                "kernel": "next-20150921",
                "errors": [
                    [1, "An error string"]
                ],
                "warnings": [
                    [10, "A warning string"]
                ]
            }
        ]
    }

 .. note::
    Results shown here do not include the full JSON response.


POST
****

.. http:post:: /job

 Update a job status once all builds have been imported.

 For more info on all the required JSON request fields, see the :ref:`job schema for POST requests <schema_job_post>`.

 :reqjson string job: The name of the job.
 :reqjson string kernel: The name of the kernel.
 :reqjson string git_branch: The name of the branch.
 :reqjson string status: The status the job should be set to (optional). By default it will be set to ``PASS``.

 :reqheader Authorization: The token necessary to authorize the request.
 :reqheader Content-Type: Content type of the transmitted data, must be ``application/json``.
 :reqheader Accept-Encoding: Accept the ``gzip`` coding.

 :resheader Content-Type: Will be ``application/json; charset=UTF-8``.

 :status 200: The request has been processed.
 :status 400: JSON data not valid.
 :status 403: Not authorized to perform the operation.
 :status 404: Document not found.
 :status 415: Wrong content type.
 :status 422: No real JSON data provided.
 :status 500: Internal server error.
 :status 503: Service maintenance.

 **Example Requests**

 .. sourcecode:: http

    POST /job HTTP/1.1
    Host: api.kernelci.org
    Content-Type: application/json
    Accept: */*
    Authorization: token

    {
        "job": "next",
        "kernel": "next-20140801",
        "git_branch": "master",
        "status": "FAIL"
    }

DELETE
******

.. http:delete:: /job/(string:id)/

 Delete the job identified by ``id``.

 :param id: The :ref:`ID <intro_schema_ids>` of the job to delete.
 :type id: string

 :reqheader Authorization: The token necessary to authorize the request.
 :reqheader Accept-Encoding: Accept the ``gzip`` coding.

 :resheader Content-Type: Will be ``application/json; charset=UTF-8``.

 :status 200: Resource deleted.
 :status 403: Not authorized to perform the operation.
 :status 404: The provided resource has not been found.
 :status 500: Internal server error.
 :status 503: Service maintenance.

 **Example Requests**

 .. sourcecode:: http

    DELETE /job/01234567890123456789ABCD HTTP/1.1
    Host: api.kernelci.org
    Accept: */*
    Content-Type: application/json
    Authorization: token

More Info
*********

* :ref:`Job schema <schema_job>`
* :ref:`API results <intro_schema_results>`
* :ref:`Schema time and date <intro_schema_time_date>`
