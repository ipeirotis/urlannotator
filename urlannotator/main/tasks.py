import subprocess

from django.conf import settings

from celery import task
from boto.s3.connection import S3Connection
from boto.s3.key import Key


@task()
def add(x, y):
    return x + y


@task()
def web_content_extraction(url):
    """ Links/lynx required. Generates html output from those browsers.
    """
    text = subprocess.check_output(["links", "-dump", url])

    conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.create_bucket('web_content')
    k = Key(bucket)
    k.key = url

    k.set_contents_from_string(text)

    return True


@task()
def web_screenshot_extraction(url):
    """ CutyCapt required. Generates html output from those browsers.
    """
    # text = subprocess.check_output(["links", "-dump", url])

    # conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
    #     settings.AWS_SECRET_ACCESS_KEY)
    # bucket = conn.create_bucket('web_content')
    # k = Key(bucket)
    # k.key = url

    # k.set_contents_from_string(text)

    # return True
