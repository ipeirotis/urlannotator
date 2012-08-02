from django.core.management.base import NoArgsCommand
from django.conf import settings

from urlannotator.main.management.commands._job_monitor import JobMonitor
from urlannotator.main.models import ProgressStatistics


class ProgressMonitor(JobMonitor):
    def __init__(self, **kwargs):
        super(ProgressMonitor, self).__init__(cls=ProgressStatistics, **kwargs)

    def get_value(self, job):
        div = job.no_of_urls or 1
        return (job.no_of_urls - job.remaining_urls) / div * 100


class Command(NoArgsCommand):
    args = 'None'
    help = ('Monitors job progress every %d s.') %\
        settings.JOB_MONITOR_INTERVAL

    def handle(self, *args, **kwargs):
        ProgressMonitor().run()
