import sys
import re
import logging
import inspect

from urlannotator.payments.models import JobCharge

log = logging.getLogger(__name__)


def dummy_handler(*args, **kwargs):
    pass


class StripeResource(object):
    """ Handles Webhook event calls from Stripe.

        `name` - Stripe resource name, e.g. `account`
                 for event `account.updated`. Refer to
                 https://stripe.com/docs/api#event_types
    """
    name = r"$^"


class DummyResource(StripeResource):
    """ Handles unsupported event calls """


class ChargeResource(StripeResource):
    name = r"charge"

    def handle_succeeded(self, **event_data):
        charge = JobCharge.objects.get(
            charge_id=event_data['data']['object']['id'])
        charge.job.initialize()


def handlers_for_res(resource, regenerate_cache=False):
    try:
        if not hasattr(handlers_for_res, "cache") or regenerate_cache:
            classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
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
    except:
        log.exception('error')


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
