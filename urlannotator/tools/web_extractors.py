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
    if settings.TOOLS_TESTING:
        return 'test'

    # Simply calling links/lynx
    return extract_words(subprocess.check_output(["links", "-dump", url]))

DEFAULT_QUALITY = 50
DEF_SCREEN_WIDTH = 1024
DEF_SCREEN_HEIGHT = 768


def get_web_screenshot(url):
    """
    Using CutyCapt application we create new file to which we point creating
    new s3 object on aws.
    This screenshot becomes public because we want permanent link for it.
    Url is put together from s3 server name and object path.
    As result we return url to screenshot.
    """
    if settings.TOOLS_TESTING:
        return url

    slugified_url = slugify(url)
    screen_dir = "urlannotator_web_screenshot"
    screen_out = "%s/%s.jpeg" % (screen_dir, slugified_url)

    # Lets create dir for temporary screenshots.
    os.system("mkdir -p %s" % screen_dir)

    capture_url = '"%s"' % url
    out = '-o %s' % screen_out
    quality = '-q %d' % DEFAULT_QUALITY
    format = '-f jpeg'
    size = '-g %d %d' % (DEF_SCREEN_WIDTH, DEF_SCREEN_HEIGHT)
    xvfb = '-x'

    params = ' '.join([capture_url, out, quality, format, size, xvfb])

    # Capturing web.
    res = os.system('python urlannotator/tools/extract_screenshot.py %s'
        % params)

    # Non-zero result code
    if res:
        raise Exception("Screenshot capture of %s resulted in code %s"
            % (url, res))

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

    # Amazon replaces some characters
    name = k.name.replace('://', '%3A/')
    name = name.replace('?', '%3F')
    name = name.replace('=', '%3D')

    # Url for public screen (without any expiration date)
    return S3_SERVER_NAME + SCREEN_DUMPS_BUCKET_NAME + '/' + name
