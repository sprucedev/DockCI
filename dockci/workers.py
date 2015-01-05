"""
Functions and constants relating to background workers
"""
import logging
import multiprocessing
import os

from flask_mail import Message

from dockci.main import Build, Job
from dockci.server import APP, MAIL


MAIL_QUEUE = multiprocessing.Queue()  # pylint:disable=no-member


def init_mail_queue():
    """
    Start the mail queue process
    """
    pid = os.fork()
    if not pid:  # child process
        with APP.app_context():
            logging.info("Email queue initiated")
            while True:
                message = MAIL_QUEUE.get()
                try:
                    MAIL.send(message)

                except Exception:  # pylint:disable=broad-except
                    logging.exception("Couldn't send email message")


def run_build_worker(job_slug, build_slug):
    """
    Load and run a build's private run job. Used to trigger builds inside
    worker threads so that data is pickled correctly
    """
    try:
        with APP.app_context():
            job = Job(job_slug)
            build = Build(job=job, slug=build_slug)
            build_okay = build._run_now()  # pylint:disable=protected-access

            # Send the failure message
            if not build_okay:
                recipients = []
                if build.git_author_email:
                    recipients.append('%s <%s>' % (
                        build.git_author_name,
                        build.git_author_email
                    ))
                if build.git_committer_email:
                    recipients.append('%s <%s>' % (
                        build.git_committer_name,
                        build.git_committer_email
                    ))

                if recipients:
                    email = Message(
                        recipients=recipients,
                        subject="DockCI - {job_name} {build_result}ed".format(
                            job_name=job.name,
                            build_result=build.result,
                        ),
                    )
                    MAIL_QUEUE.put_nowait(email)

    except Exception:  # pylint:disable=broad-except
        logging.exception("Something went wrong in the build worker")
