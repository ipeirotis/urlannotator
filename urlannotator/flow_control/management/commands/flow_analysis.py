from itertools import groupby

from django.core.management.base import BaseCommand
from urlannotator.flow_control.event_system import flow_modules


def strip_prefix(name):
    return '.'.join(name.split('.')[1:])


def strip_name(name):
    return ('.'.join(strip_prefix(name).split('.')[:-1]))


def get_flow_definitions():
    flows_definitions = [x for m in flow_modules() for x in m.FLOW_DEFINITIONS]
    key = lambda x: x[0]
    s = sorted(flows_definitions, key=key)
    return dict((k, [strip_prefix(x[1].name) for x in l])
        for k, l in groupby(s, key=key))


class Command(BaseCommand):
    args = ''
    help = 'analyses event handing'

    def handle(self, *args, **options):
        w = get_flow_definitions()
        for ev, handlers in w.iteritems():
            print ev
            for handler in handlers:
                print '   ', handler
            print
