import os

from tenclouds.imagescale2.settings import *

DEF_HOST = '0.0.0.0'
DEF_PORT = 12345

DEF_WIDTH = 100
DEF_HEIGHT = 100
DEF_USE_FIT = False

HASHING_ALGORITHM = 'md5'
SALT = ''

local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from local import *

AUTHORISATION = ('SaltedUrlHash', [HASHING_ALGORITHM, SALT], {})
