from django.conf import settings
from django.utils.importlib import import_module


def load():
    """
    Loader for automatic settings.FLOW_DEFINITIONS population. Each
    FLOW_DEFINITIONS is placed in events module in django apps.
    """

    for app in settings.INSTALLED_APPS:
        try:
            import_module('%s.events' % app)
        except:
            pass
