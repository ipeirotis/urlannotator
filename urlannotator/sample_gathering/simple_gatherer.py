from celery import task, Task, registry

from urlannotator.main.models import Job, Sample

# Number of seconds between each gather
TIME_INTERVAL = 2 * 60

# Maximum number of samples collected per run
SAMPLE_LIMIT = 20


@task(ignore_result=True)
class SimpleGatherer(Task):
    """
        Simple sample gatherer that is run on fixed interval.
    """
    def run(self, *args, **kwargs):
        jobs = Job.objects.get_active().filter(remaining_urls__gt=0)
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
                Sample.objects.create_by_owner(
                    job_id=job.id,
                    url=urls[i]
                )
                collected += 1
                i = (i + 1) % len(urls)
            job.remaining_urls -= collected
            job.save()
            to_collect -= collected

simple_gatherer = registry.tasks[SimpleGatherer.name]
