"""
Generic DockCI utils
"""
import hashlib
import hmac
import logging
import os
import re
import socket
import struct
import json
import datetime

from contextlib import contextmanager
from ipaddress import ip_address

from flask import flash, request


def is_yaml_file(filename):
    """
    Check if the filename provided points to a file, and ends in .yaml
    """
    return os.path.isfile(filename) and filename.endswith('.yaml')


def request_fill(model_obj, fill_atts, save=True):
    """
    Fill given model attrs from a POST request (and ignore other requests).
    Will save only if the save flag is True
    """
    print(request.method)
    if request.method == 'POST':
        for att in fill_atts:
            if att in request.form:
                setattr(model_obj, att, request.form[att])
            else:
                setattr(model_obj, att, None)

        if save:
            model_obj.save()
            flash(u"%s saved" % model_obj.__class__.__name__.title(),
                  'success')


def default_gateway():
    """
    Gets the IP address of the default gateway
    """
    with open('/proc/net/route') as handle:
        for line in handle:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                continue

            return ip_address(socket.inet_ntoa(
                struct.pack("<L", int(fields[2], 16))
            ))


def bytes_human_readable(num, suffix='B'):
    """
    Gets byte size in human readable format
    """
    for unit in ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'):
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1000.0

    return "%.1f%s%s" % (num, 'Y', suffix)


def is_valid_github(secret):
    """
    Validates a GitHub hook payload
    """
    if 'X-Hub-Signature' not in request.headers:
        return False

    hash_type, signature = request.headers['X-Hub-Signature'].split('=')
    if hash_type.lower() != 'sha1':
        logging.warn("Unknown GitHub hash type: '%s'", hash_type)
        return False

    computed_signature = hmac.new(secret.encode(),
                                  request.data,
                                  hashlib.sha1).hexdigest()

    return signature == computed_signature


@contextmanager
def stream_write_status(handle, status, success, fail):
    """
    Context manager to write a status, followed by success message, or fail
    message if yield raises an exception
    """
    handle.write(status.encode())
    try:
        yield
        handle.write((" %s\n" % success).encode())
    except Exception:  # pylint:disable=broad-except
        handle.write((" %s\n" % fail).encode())
        raise


# pylint:disable=too-few-public-methods
class DateTimeEncoder(json.JSONEncoder):
    """
    Encode a date/time for JSON dump
    """
    def default(self, obj):  # pylint:disable=method-hidden
        if isinstance(obj, datetime.datetime):
            encoded_object = list(obj.timetuple())[0:6]

        else:
            encoded_object = super(DateTimeEncoder, self).default(obj)

        return encoded_object


def is_semantic(version):
    """
    Returns True if tag contains a semantic version number prefixed with a
    lowercase v.  e.g. v1.2.3 returns True
    """
    # TODO maybe this could be a configuable regex for different
    # versioning schemes?  (yyyymmdd for example)
    return re.match(r'^v\d+\.\d+\.\d+$', version) is not None
