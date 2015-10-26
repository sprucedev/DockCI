"""
Functions and constants relating to background workers
"""
import logging
import os
import tempfile

import py.path  # pylint:disable=import-error
import rollbar

from flask_mail import Message

from dockci.models.job import Job
from dockci.server import APP, MAIL


def start_workers():
    """ Start the worker manager process to pop new jobs off the queue """
    if os.fork():
        return
    while True:
        job_id = APP.worker_queue.get()
        run_job_async(job_id)


def send_mail(message):
    """
    Send an email using the app context
    """
    with APP.app_context():
        try:
            MAIL.send(message)

        except Exception:  # pylint:disable=broad-except
            rollbar.report_exc_info()
            logging.getLogger('dockci.mail').exception(
                "Couldn't send email message"
            )


def run_job_async(job_id):
    """
    Load and run a job's private run project, forking to handle the job in
    the background
    """
    if os.fork():
        return  # parent process

    with APP.app_context():
        job = Job.query.get(job_id)
        with tempfile.TemporaryDirectory() as workdir:
            # pylint:disable=protected-access
            workdir = py.path.local(workdir)
            job._run_now(workdir)
            changed_result = job.changed_result(workdir)

        project = job.project

        # Send the failure message
        if changed_result:
            recipients = []
            if job.git_author_email:
                recipients.append('%s <%s>' % (
                    job.git_author_name,
                    job.git_author_email
                ))
            if job.git_committer_email:
                recipients.append('%s <%s>' % (
                    job.git_committer_name,
                    job.git_committer_email
                ))

            if recipients:
                subject = (
                    "DockCI - {project_name} {job_result}ed".format(
                        project_name=project.name,
                        job_result=job.result,
                    )
                )
                email = Message(
                    recipients=recipients,
                    subject=subject,
                )
                send_mail(email)
