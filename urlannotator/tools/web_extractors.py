import httplib
import urlparse
import subprocess
import os
import re

from django.conf import settings
from django.template.defaultfilters import slugify
from itertools import ifilter

from boto.s3.connection import S3Connection
from boto.s3.key import Key

SCREEN_DUMPS_BUCKET_NAME = "urlannotator_web_screenshot"
S3_SERVER_NAME = "https://s3.amazonaws.com/"


def url_status(url):
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(netloc)
    conn.request("HEAD",
        urlparse.urlunparse(('', '', path, params, query, fragment)))
    res = conn.getresponse()
    print res.status

BLACKLISTED_WORDS = ['img']


def extract_words(text):
    """
        Finds all words starting and ending with a character, with possible
        delimiters in the middle.
    """
    # \w matches [a-zA-Z0-9_], and we dont want underscores at both ends
    words = re.findall(r"[a-zA-Z0-9][\w'\-\.]*[a-zA-Z0-9]", text)

    words = ifilter(lambda line: line not in BLACKLISTED_WORDS, words)

    # Join found words, and lowercase them
    text = ' '.join(words).lower()

    # Remove continous delimiters
    text = re.sub(r"[']{2,}", "'", text)
    text = re.sub(r'[-]{2,}', '-', text)
    text = re.sub(r'[_]{2,}', '_', text)
    text = re.sub(r'[\.]{2,}', '.', text)
    return text


def get_web_text(url):
    """ Using links we extract content from web.
    """

    # Simply calling links/lynx
    return extract_words(subprocess.check_output(["links", "-dump", url]))


def get_web_screenshot(url):
    """
    Using CutyCapt application we create new file to which we point creating
    new s3 object on aws.
    This screenshot becomes public because we want permanent link for it.
    Url is put together from s3 server name and object path.
    As result we return url to screenshot.
    """

    slugified_url = slugify(url)
    screen_dir = "urlannotator_web_screenshot"
    screen_out = "%s/%s.png" % (screen_dir, slugified_url)

    # Lets create dir for temporary screenshots.
    os.system("mkdir -p %s" % screen_dir)
    # Capturing web.
    res = os.system('xvfb-run --auto-servernum cutycapt --url="%s" --out="%s"'
        % (url, screen_out))

    # Non-zero result code
    if res:
        print "Screenshot capture of", url, "resulted in code", res

    conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.create_bucket(SCREEN_DUMPS_BUCKET_NAME)
    k = Key(bucket)
    k.key = url
    # Set key to desired screenshot.
    k.set_contents_from_filename(screen_out)

    # Removing file from disc
    os.system('rm %s' % screen_out)

    # Give access to view screen.
    k.make_public()

    # Amazon replaces 'http://' with 'http%3A/'
    name = k.name.replace('://', '%3A/')

    # Url for public screen (without any expiration date)
    return S3_SERVER_NAME + SCREEN_DUMPS_BUCKET_NAME + '/' + name
