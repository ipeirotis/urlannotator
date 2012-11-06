from urlannotator.payments.backends import DummyBackend

initializers = {
    'DummyBackend': DummyBackend,
}


class PaymentFactory(object):
    def get_backend_for_job(job):
        settings = job.jobpaymentsettings_set.get(main=True)
        backend_class = initializers.get(settings.backend, DummyBackend)
        params = settings.backend_settings
        return backend_class(**params)
