import json

from django.core.management.base import BaseCommand

from urlannotator.flow_control import send_event


class Command(BaseCommand):
    args = ''
    help = """
        Send events with json encoded kwargs. Example:
        ./manage.py send_event EventNewSample '{"sample_id":1, "job_id":1}'
    """

    def handle(self, event_name, event_kwargs=None, *args, **options):
        kwargs = {}
        if event_kwargs:
            kwargs = json.loads(event_kwargs)

        # We don't use args with send_event!
        send_event(event_name, **kwargs)
