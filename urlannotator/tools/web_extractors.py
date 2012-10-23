import urlparse
import subprocess
import os
import re
import socket
import struct

from django.conf import settings
from django.template.defaultfilters import slugify
from itertools import ifilter

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from urlannotator.tools.utils import os_result_to_code, DiffbotClient
from urlannotator.tools.webkit2png import error_code_to_exception

import logging
log = logging.getLogger(__name__)

SCREEN_DUMPS_BUCKET_NAME = "urlannotator_web_screenshot"
S3_SERVER_NAME = "https://s3.amazonaws.com/"

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


def makeMask(n):
    """
        Return a mask of n bits as a long integer.
    """
    right_offset = 32 - n
    right_bytes = (1L << right_offset) - 1
    full_mask = 0xFFFFFFFF
    return full_mask ^ right_bytes


def dottedQuadToNum(ip):
    """
        Convert decimal dotted string to long integer.
        Supports all formats suitable for C inet_aton function.
    """
    return struct.unpack('>L', socket.inet_aton(ip))[0]


def addressInNetwork(ip, net, bits):
    """
        Is an address in a network.
    """
    bits = makeMask(bits)
    return ip & bits == net & bits


def is_proper_url(url):
    """
        Checks whether the URL points to a valid location.
    """
    _, netloc, path, _, _, _ = urlparse.urlparse(url)
    url = netloc if netloc else path

    # Remove port from the url.
    url = url.split(':', 1)[0]

    if not url or url == 'localhost':
        return False

    # IPv4 address?
    try:
        address = dottedQuadToNum(url)
        disallowed_ipv4 = [
            (dottedQuadToNum('10.0.0.0'), 8),
            (dottedQuadToNum('172.16.0.0'), 12),
            (dottedQuadToNum('192.168.0.0'), 16),
            (dottedQuadToNum('127.0.0.1'), 32),
        ]
        res = map(lambda x: addressInNetwork(address, x[0], x[1]), disallowed_ipv4)
        if any(res):
            return False
    except:
        # Address is not a valid IPv4 address
        pass

    return True


def links_extractor(url):
    """ Using links we extract content from web.
    """
    # Simply calling links/lynx
    text = subprocess.check_output(["links", "-dump", url])
    return extract_words(text)


def diffbot_extractor(url):
    """
        Extracts page content using Diffbot Article API.
    """
    try:
        client = DiffbotClient(settings.DIFFBOT_TOKEN)
        content = client.get_article({
            'url': url,
        })
        return extract_words(content)
    except Exception, e:
        log.exception(
            '[DiffBot] Exception while getting url %s.' % url
        )
        return ''


def get_web_text(url):
    """ Using links we extract content from web.
    """
    # # Firstly, check if Diffbot can extract the content
    # content = diffbot_extractor(url)
    # if not content:
    #     log.warning(
    #         '[TextExtract] Diffbot failed to extract %s : %s.'
    #         'Falling back to Links' % (url, content)
    #     )
    content = links_extractor(url)
    return content

DEFAULT_QUALITY = 50
DEF_SCREEN_WIDTH = 1024
DEF_SCREEN_HEIGHT = 768


def capture_web_screenshot(url, out_path):
    """
        Performs screenshot capture of the `url` to `out_path` destination.
        Throws exceptions depending on return code.
        See webkit2png.error_code_to_exception(code) for reference.
    """
    # Sanitize url
    url = url.replace('"', '%22')

    capture_url = '"%s"' % url
    out = '-o %s' % out_path
    quality = '-q %d' % DEFAULT_QUALITY
    format = '-f jpeg'
    size = '-g %d %d' % (DEF_SCREEN_WIDTH, DEF_SCREEN_HEIGHT)
    xvfb = '-x'

    params = ' '.join([out, quality, format, size, xvfb, capture_url])

    # Capturing web.
    res = os.system('python urlannotator/tools/extract_screenshot.py %s'
        % params)

    res = os_result_to_code(res)
    # Non-zero result code
    if res:
        error_code_to_exception(res)


def upload_to_s3(filename, key=''):
    """
        Uploads given filename to s3 bucket and makes it public. Returns URL
        of uploaded resource.

        :param key: Key of the uploaded resource. Defaults to `filename`.
    """
    conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.create_bucket(SCREEN_DUMPS_BUCKET_NAME)
    k = Key(bucket)
    k.key = key if key else filename
    # Set key to desired screenshot.
    k.set_contents_from_filename(filename)

    # Give access to view screen.
    k.make_public()

    # Amazon replaces some characters
    name = k.name.replace('%', '%25')
    name = name.replace('://', '%3A/')
    name = name.replace('?', '%3F')
    name = name.replace('=', '%3D')
    name = name.replace('+', '%2B')

    # Url for public screen (without any expiration date)
    return S3_SERVER_NAME + SCREEN_DUMPS_BUCKET_NAME + '/' + name


def get_web_screenshot(url):
    """
    Create new file to which we point creating new s3 object on aws.
    This screenshot becomes make_publiclic because we want permanent link for it.
    Url is put together from s3 server name and object path.
    As result we return url to screenshot.
    """
    slugified_url = slugify(url)
    screen_dir = "urlannotator_web_screenshot"
    screen_out = "%s/%s.jpeg" % (screen_dir, slugified_url)

    # Lets create dir for temporary screenshots.
    os.system("mkdir -p %s" % screen_dir)
    capture_web_screenshot(url=url, out_path=screen_out)

    url = upload_to_s3(screen_out)

    # Removing file from disc
    os.system('rm %s' % screen_out)

    return url
