import sys
import re
import logging
import inspect
import stripe

from django.conf import settings

from urlannotator.payments.models import JobCharge

log = logging.getLogger(__name__)


def stripe_client():
    stripe.api_key = settings.STRIPE_SECRET
    return stripe


def dummy_handler(*args, **kwargs):
    pass


class StripeResource(object):
    """ Handles Webhook event calls from Stripe.

        `name` - Stripe resource name, e.g. `account`
                 for event `account.updated`. Refer to
                 https://stripe.com/docs/api#event_types
    """
    name = r"$^"

    @staticmethod
    def _object_id(**event_data):
        return event_data['data']['object']['id']


class DummyResource(StripeResource):
    """ Handles unsupported event calls """


class ChargeResource(StripeResource):
    name = r"charge"

    @staticmethod
    def _get_charge(**event_data):
        return JobCharge.objects.\
            get(charge_id=ChargeResource._object_id(**event_data))

    def handle_succeeded(self, **event_data):
        self._get_charge(**event_data).job.initialize()

    def handle_refunded(self, **event_data):
        charge = self._get_charge(**event_data)
        charge.job.stop()
        data = {
            'charge_id': charge.charge_id,
            'job_id': charge.job_id,
        }
        log.warning(
            'Stripe callback: Charge {charge_id} for job {job_id} '
            'has got refunded! The job has been stopped.'.format(**data)
        )

    def handle_failed(self, **event_data):
        charge = self._get_charge(**event_data)
        charge.job.stop()
        data = {
            'charge_id': charge.charge_id,
            'job_id': charge.job_id,
        }
        log.warning(
            'Stripe callback: Charge {charge_id} for job {job_id} '
            'has failed! The job has been stopped.'.format(**data)
        )

    def handle_dispute_created(self, **event_data):
        charge = self._get_charge(**event_data)
        charge.job.stop()
        data = {
            'charge_id': charge.charge_id,
            'job_id': charge.job_id,
        }
        log.warning(
            'Stripe callback: Charge {charge_id} for job {job_id} '
            'was disputed! The job will be stopped.'.format(**data)
        )


def handlers_for_res(resource, regenerate_cache=False):
    if not hasattr(handlers_for_res, "cache") or regenerate_cache:
        classes = inspect.getmembers(
            sys.modules[__name__], inspect.isclass)

        handlers_for_res.cache = [(re.compile(obj.name), obj)
            for name, obj in classes
            if issubclass(obj, StripeResource)]

    matched = False
    for reg, handler in handlers_for_res.cache:
        if reg.match(resource):
            matched = True
            yield handler()

    if not matched:
        yield DummyResource()


def handle_event(event_type, event_data):
    data = event_type.split('.', 1)
    event_resource = data[0]
    event_name = data[1].replace('.', '_')
    for handler in handlers_for_res(event_resource):
        try:
            fun_name = "handle_{0}".format(event_name)
            fun = getattr(handler, fun_name, dummy_handler)
            fun(**event_data)
        except:
            log.exception(
                "Stripe: Handler {0} for event {1} failed".format(handler,
                    event_type)
            )
