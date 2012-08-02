from django.core.management.base import NoArgsCommand
from django.conf import settings

from urlannotator.main.management.commands._job_monitor import JobMonitor
from urlannotator.main.models import SpentStatistics


class SpentMonitor(JobMonitor):
    def __init__(self, **kwargs):
        super(SpentMonitor, self).__init__(cls=SpentStatistics, **kwargs)

    def get_value(self, job):
        return job.budget


class Command(NoArgsCommand):
    args = 'None'
    help = ('Monitors job money spent every %d s.') %\
        settings.JOB_MONITOR_INTERVAL

    def handle(self, *args, **kwargs):
        SpentMonitor().run()
