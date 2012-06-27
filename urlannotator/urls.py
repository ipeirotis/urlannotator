from django.conf import settings
from django.conf.urls import patterns, include, url
from registration import backends
from django.contrib import admin
admin.autodiscover()


def bad(request):
    """ Simulates a server error """
    1 / 0

urlpatterns = patterns('urlannotator',

    url(r'^$', 'main.views.index', name='index'),
    url(r'^register$', 'main.views.register_view', name='register'),
    url(r'^activation/(?P<key>.+)$', 'main.views.activation_view', name='activation'),
    url(r'^login$', 'main.views.login_view', name='login'),
    url(r'^logout$', 'main.views.logout_view', name='logout'),
    url(r'^facebook_login$', 'main.views.facebook_login', name='fb_login'),    
    url(r'^gplus_login$', 'main.views.gplus_login', name='gplus_login'),
    url(r'^twitter_login$', 'main.views.twitter_login', name='twitter_login'),
    url(r'^odesk_login$', 'main.views.odesk_login', name='odesk_login'),
    url(r'^password_recovery$', 'main.views.pass_recover', name="pass_recover"),
    url(r'^_admin/', include(admin.site.urls)),

    (r'^bad/$', bad),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
