# Copyright (C) Baylibre 2019
# Author: Khouloud Touil <ktouil@baylibre.com>
#
# Copyright (C) Collabora Limited 2017,2018,2019
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Ana Guerrero Lopez <ana.guerrero@collabora.com>
#
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

"""All reports related celery tasks."""

import models
import taskqueue.celery as taskc
import utils.db
import utils.emails
import utils.report.bisect
import utils.report.build
import utils.report.common
import utils.report.error
import utils.report.test


@taskc.app.task(name="send-build-report")
def send_build_report(job, git_branch, kernel, email_opts):
    """Create the build report email and send it.

    :param job: The job name.
    :type job: string
    :param git_branch: The git branch name.
    :type git_branch: string
    :param kernel: The kernel name.
    :type kernel: string
    :param email_opts: Email options.
    :type email_opts: dict
    """
    utils.LOG.info(
        "Preparing build report email for '%s-%s-%s'", job, git_branch, kernel)
    status = "ERROR"

    db_options = taskc.app.conf.get("db_options", {})

    txt_body, html_body, new_subject, headers = \
        utils.report.build.create_build_report(
            job,
            git_branch,
            kernel,
            email_opts["format"],
            db_options=db_options,
            mail_options=taskc.app.conf.get("mail_options", None)
        )

    subject = email_opts.get("subject") or new_subject

    if (txt_body or html_body) and subject:
        utils.LOG.info("Sending build report email for '%s-%s'", job, kernel)
        status, errors = utils.emails.send_email(
            subject, txt_body, html_body, email_opts,
            taskc.app.conf.mail_options, headers
        )
        utils.report.common.save_report(
            job, git_branch, kernel, models.BUILD_REPORT,
            status, errors, db_options
        )
    else:
        utils.LOG.error(
            "No email body nor subject found for build report '{}-{}-{}'"
            .format(job, git_branch, kernel))

    return status


@taskc.app.task(name="send-bisect-report")
def send_bisect_report(report_data, email_opts, base_path=utils.BASE_PATH):
    """Send the bisect report email.

    :param report_data: The data necessary for generating a report.
    :type report_data: dict
    :param email_opts: Email options.
    :type email_opts: dict
    """
    status = "ERROR"
    job, git_branch, kernel = (report_data[k] for k in [
        models.JOB_KEY,
        models.GIT_BRANCH_KEY,
        models.KERNEL_KEY,
    ])
    report_id = "-".join([job, git_branch, kernel])

    utils.LOG.info("Sending bisect report email for {}".format(report_id))

    db_options = taskc.app.conf.get("db_options", {})

    report_data = utils.report.bisect.create_bisect_report(
        report_data, email_opts, db_options)

    if not report_data:
        return status

    body, headers = report_data
    status, errors = utils.emails.send_email(
        email_opts["subject"], body, None, email_opts,
        taskc.app.conf.mail_options, headers)

    utils.report.common.save_report(
        job, git_branch, kernel, models.BISECT_REPORT,
        status, errors, db_options)

    return status


@taskc.app.task(name="send-test-report")
def send_test_report(job, git_branch, kernel, plan, report_data, email_opts):
    """Send the tests report email.

    :param job: The job name.
    :type job: string
    :param git_branch: The git branch name.
    :type git_branch: string
    :param kernel: The kernel name.
    :type kernel: string
    :param plan: Test plan to include in the report.
    :type plan: string
    :param report_data: The data necessary for generating a report.
    :type report_data: dict
    :param email_opts: Email options.
    :type email_opts: dict
    """
    report_id = "-".join([job, git_branch, kernel, plan])
    utils.LOG.info("Sending tests report email for '{}'".format(report_id))

    db_options = taskc.app.conf.get("db_options", {})

    test_report = utils.report.test.create_test_report(
        db_options, report_data, email_opts["format"], email_opts["template"])

    if test_report is None:
        return 500

    body, subject, headers = test_report

    if body is None:
        return 200

    status, errors = utils.emails.send_email(
        subject, body, None, email_opts, taskc.app.conf.mail_options, headers)

    utils.report.common.save_report(
        job, git_branch, kernel, models.TEST_REPORT,
        status, errors, db_options)

    return status


@taskc.app.task(name="send-multi-email-errors-report")
def send_multiple_emails_error(
        job, git_branch, kernel, date, email_format, email_type, data):

    email_data = {
        "job": job,
        "git_branch": git_branch,
        "kernel": kernel,
        "trigger_time": date,
        "email_format": email_format,
        "email_type": email_type,
        "to_addrs": data.get("to"),
        "cc_addrs": data.get("cc"),
        "subject": data.get("subject"),
        "in_reply_to": data.get("in_reply_to"),
        "trigger_time": date
    }

    db = utils.db.get_db_connection2(taskc.app.conf.db_options)
    result = utils.db.find_one2(
        db[models.JOB_COLLECTION],
        {
            models.JOB_KEY: job,
            models.KERNEL_KEY: kernel,
            models.GIT_BRANCH_KEY: git_branch
        },
        [
            models.GIT_COMMIT_KEY,
            models.GIT_DESCRIBE_V_KEY,
            models.KERNEL_VERSION_KEY,
            models.GIT_URL_KEY
        ])

    if result:
        email_data.update(result)

    txt_body, html_body, subject = \
        utils.report.error.create_duplicate_email_report(email_data)

    if (txt_body or html_body) and subject:
        utils.LOG.info(
            "Sending duplicate emails report for %s-%s-%s",
            job, git_branch, kernel)
        email_opts = {"to": [taskc.app.conf.mail_options["error_email"]]}
        utils.emails.send_email(subject, txt_body, html_body, email_opts,
                                taskc.app.conf.mail_options)
