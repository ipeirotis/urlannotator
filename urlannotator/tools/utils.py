import platform
import urlparse

from django.conf import settings


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
