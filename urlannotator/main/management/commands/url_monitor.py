from django.core.management.base import NoArgsCommand
from django.conf import settings

from urlannotator.main.management.commands._job_monitor import JobMonitor
from urlannotator.main.models import URLStatistics


class URLMonitor(JobMonitor):
    def __init__(self, **kwargs):
        super(URLMonitor, self).__init__(cls=URLStatistics, **kwargs)

    def get_value(self, job):
        return job.no_of_urls - job.remaining_urls


class Command(NoArgsCommand):
    args = 'None'
    help = ('Monitors job urls collected every %d s.') %\
        settings.JOB_MONITOR_INTERVAL

    def handle(self, *args, **kwargs):
        URLMonitor().run()
