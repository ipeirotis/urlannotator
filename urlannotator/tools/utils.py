import platform
import urlparse
import requests
import json
import re

from django.conf import settings

import logging
log = logging.getLogger(__name__)


def os_result_to_code(code):
    """
        Transforms os.system call's result number into real error code.

        As of os.system documentation:
            - On Unix - returns what os.wait() returns: a 16-bit number, whose
                        low byte is the signal number that killed the process,
                        and whose high byte is the exit status (if the signal
                        number is zero); the high bit of the low byte is set if
                        a core file was produced.
            - On Windows - 0 for systems using command.com (95, 98 and ME),
                           return code for systems using cmd.exe (NT, 2000, XP)

        Raises Exceptions if os.system is not available.
    """
    import os
    if not hasattr(os, 'system'):
        raise Exception('os.system() is not available on this platform.')

    os = platform.system()
    unix_systems = ['Linux']
    if os in unix_systems:
        high_byte = (code & 0xFF00) >> 8
        return high_byte

    return code


def setting(name, default):
    """
        Returns a settings value. If not present, returns `default`.
    """
    return getattr(settings, name, default)


def sanitize_url(url):
    result = urlparse.urlsplit(url)
    if not result.scheme:
        return 'http://%s' % url
    return url


class DiffbotClient(object):
    """
    A simple Python interface for the Diffbot api.
    Relies on the Requests library - python-requests.org

    Usage:
    YOUR_DIFFBOT_DEV_TOKEN = '12345'

    diffbot = Diffbot(YOUR_DIFFBOT_DEV_TOKEN)

    diffbot.get_article({
    'url': 'http://example.com/page',
    })

    diffbot.get_frontpage({
    'url': 'http://example.com',
    })

    by david-torres (https://gist.github.com/1337245)
    """
    output_format = 'json'

    def __init__(self, dev_token):
        self.dev_token = dev_token

    def get_article(self, params={}):
        api_endpoint = 'http://www.diffbot.com/api/article'
        params.update({
            'token': self.dev_token,
            'format': self.output_format,
        })
        r = requests.get(api_endpoint, params=params)
        content = json.loads(r.content)

        if r.status_code >= 400 or 'error' in content:
            log.warning(
                '[Diffbot] Error while getting url %s: %s.'
                % (params['url'], content)
            )
            return ''

        return content['text']

    def get_frontpage(self, params={}):
        api_endpoint = 'http://www.diffbot.com/api/frontpage'
        params.update({
            'token': self.dev_token,
            'format': self.output_format,
        })
        r = requests.get(api_endpoint, params=params)
        return json.loads(r.content)


url_correct_re = re.compile(
    r'^(?:http|ftp)s?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def url_correct(url):
    return bool(url_correct_re.match(url))


def cached(fun):
    def wrapper(*args, **kwargs):
        from django.core.cache import get_cache

        cache_name = kwargs.pop('cache_name', 'memcache')
        cache_key = kwargs.pop('cache_key')
        cache_time = kwargs.pop('cache_time', 0)
        cache = kwargs.get('cache', False)
        mc = get_cache(cache_name)
        val = mc.get(cache_key)
        if val is not None and cache:
            return val

        val = fun(*args, **kwargs)
        mc.set(cache_key, val, cache_time)
        return val
    return wrapper
