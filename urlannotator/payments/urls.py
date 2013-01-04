from django.conf.urls import patterns, url

urlpatterns = patterns('urlannotator.payments',

    url(r'^stripe_callback$', 'views.stripe_callback', name='stripe_callback'),
)
