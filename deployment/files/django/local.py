from defaults import *
MEDIA_ROOT = os.path.join(ROOT_PATH, 'media')
STATIC_ROOT = os.path.join(PROJECT_PATH, 'collected_static')
STATIC_URL = '/static/'

TIME_ZONE = 'UTC'
CACHE_BACKEND = 'dummy:///'

# sudo -u postgres psql
# CREATE USER mturk_tracker WITH CREATEDB NOCREATEUSER ENCRYPTED PASSWORD E'mturk_tracker';
# CREATE DATABASE mturk_tracker_db WITH OWNER mturk_tracker;

DB = DATABASES['default']
DATABASE_NAME = DB['NAME']
DATABASE_USER = DB['USER']
DATABASE_PASSWORD = DB['PASSWORD']

#INSTALLED_APPS = tuple(list(INSTALLED_APPS) + [])

USE_CACHE = False
CACHES = {}

SOLR_MAIN = "http://localhost:8983/solr/en"

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': SOLR_MAIN,
        # ...or for multicore...
        # 'URL': 'http://127.0.0.1:8983/solr/mysite',
    },
}
