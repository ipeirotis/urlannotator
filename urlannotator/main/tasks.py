import subprocess

from django.conf import settings

from celery import task
from boto.s3.connection import S3Connection

from urlannotator.main.models import Sample


@task()
def add(x, y):
    return x + y


@task()
def html_content_extraction(sample_id):
    """ Links/lynx required. Generates html output from those browsers.
    """

    # conn = S3Connection(settings., '<aws secret key>')

    sample = Sample.objects.get(id=sample_id)
    sample.text = subprocess.check_output(["links", "-dump", sample.url])
    sample.save()
    return True
