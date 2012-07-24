import sys
import os
import time

FILE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.join(FILE_DIR, '..', '..')

sys.path.append(ROOT_DIR)

from urlannotator.main.models import Job, Worker
from urlannotator.flow_control import send_event

# Number of seconds between each gather
TIME_INTERVAL = 30


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
            for job in jobs:
                for j in xrange(job.remaining_urls):
                    send_event('EventNewRawSample', job.id, w.id, urls[i])
                    i = (i + 1) % len(urls)
                job.remaining_urls = 0
                job.save()
            time.sleep(TIME_INTERVAL)

SimpleGatherer().run()
