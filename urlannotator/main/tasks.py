import os
import subprocess

from django.conf import settings
from django.template.defaultfilters import slugify

from celery import task
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from urlannotator.main.models import Sample

SCREEN_DUMPS_BUCKET_NAME = "urlannotator_web_screenshot"
S3_SERVER_NAME = "https://s3.amazonaws.com/"


@task()
def add(x, y):
    return x + y


@task()
def web_content_extraction(sample_id, url=None):
    """ Links/lynx required. Generates html output from those browsers.
    """
    if url is None:
        url = Sample.objects.get(id=sample_id).url

    text = subprocess.check_output(["links", "-dump", url])
    Sample.objects.get(id=sample_id).update(text=text)

    return True


@task()
def web_screenshot_extraction(sample_id, url=None):
    """ CutyCapt required. Generates html output from those browsers.
    """
    if url is None:
        url = Sample.objects.get(id=sample_id).url

    slugified_url = slugify(url)
    screen_dir = "urlannotator_web_screenshot"
    screen_out = "%s/%s.png" % (screen_dir, slugified_url)

    os.system("mkdir %s" % screen_dir)
    os.system('cutycapt --url="%s" --out="%s"' % (url, screen_out))

    conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.create_bucket(SCREEN_DUMPS_BUCKET_NAME)
    k = Key(bucket)
    k.key = url
    k.set_contents_from_filename(screen_out)

    # Give access to view screen.
    k.make_public()

    # Url for public screen (without any expiration date)
    screenshot_url = S3_SERVER_NAME + SCREEN_DUMPS_BUCKET_NAME + '/' + k.name

    Sample.objects.get(id=sample_id).update(screenshot=screenshot_url)

    return True
