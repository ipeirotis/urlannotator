import time

from django.core.management.base import NoArgsCommand

from urlannotator.main.models import Job, Worker
from urlannotator.flow_control import send_event

# Number of seconds between each gather
TIME_INTERVAL = 2 * 60

# Maximum number of samples collected per run
SAMPLE_LIMIT = 20


class SimpleGatherer(object):
    """
        Simple sample gatherer that is run on fixed interval.
    """
    def run(self, *args, **kwargs):
        while True:
            jobs = Job.objects.filter(remaining_urls__gt=0, status=1)
            w = Worker.objects.create()
            urls = [
                'google.com',
                'wikipedia.org',
                'http://www.dec.ny.gov/animals/9358.html',
                'http://www.enchantedlearning.com/subjects/mammals/raccoon/Raccoonprintout.shtml']
            i = 0
            to_collect = SAMPLE_LIMIT
            for job in jobs:
                if to_collect == 0:
                    break

                collected = 0
                for j in xrange(min(job.remaining_urls, to_collect)):
                    send_event('EventNewRawSample', job.id, w.id, urls[i])
                    collected += 1
                    i = (i + 1) % len(urls)
                job.remaining_urls -= collected
                job.save()
                to_collect -= collected
            time.sleep(TIME_INTERVAL)


class Command(NoArgsCommand):
    args = 'None'
    help = 'Starts simple gatherer that creates up to %d samples every %d s.'\
        % (SAMPLE_LIMIT, TIME_INTERVAL)

    def handle(self, *args, **kwargs):
        SimpleGatherer().run()
