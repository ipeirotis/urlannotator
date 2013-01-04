import logging
import stripe

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils import simplejson
from django.conf import settings

from urlannotator.payments.stripe_handlers import handle_event

log = logging.getLogger(__name__)


@csrf_exempt
def stripe_callback(request):
    method = request.method
    content = request.body
    try:
        content = simplejson.loads(content)
    except:
        content = {}

    event_id = str(content['id']) if 'id' in content else ""
    if not event_id:
        log.warning('Stripe callback: Received malformed event id in request.')
        return HttpResponseBadRequest()

    data = {
        'method': method,
        'content': content,
        'id': event_id,
    }
    log.debug("Stripe callback: {method} {id} {content}".format(**data))

    # Retrieve event data from Stripe so we will get correct event data
    stripe.api_key = settings.STRIPE_SECRET
    try:
        event = stripe.Event.retrieve(event_id)
        event = event.to_dict()
    except stripe.InvalidRequestError, e:
        log.exception('Stripe callback: Error while retrieving event')
        return HttpResponseBadRequest(e.message)
    except:
        log.exception('Stripe callback: Error while retrieving event')
        return HttpResponseBadRequest()

    handle_event(event['type'], event)
    return HttpResponse()
