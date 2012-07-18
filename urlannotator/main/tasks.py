from celery import task

from urlannotator.main.models import TemporarySample, Sample, Job, Worker
from urlannotator.tools.web_extractors import get_web_text, get_web_screenshot


@task()
def add(a, b):
    """ Simple queue testing task.
    """

    return a + b


@task()
def web_content_extraction(sample_id, url=None):
    """ Links/lynx required. Generates html output from those browsers.
    """
    print 'c'
    if url is None:
        url = TemporarySample.objects.get(id=sample_id).url

    text = get_web_text(url)
    TemporarySample.objects.filter(id=sample_id).update(text=text)

    print 'done c'
    return True


@task()
def web_screenshot_extraction(sample_id, url=None):
    """ CutyCapt required. Generates html output from those browsers.
    """
    print 'b'
    if url is None:
        url = TemporarySample.objects.get(id=sample_id).url

    try:
        screenshot = get_web_screenshot(url)
    except Exception, e:
        raise web_content_extraction.retry(exc=e, countdown=60)

    TemporarySample.objects.filter(id=sample_id).update(
        screenshot=screenshot)

    print 'done b'
    return True


@task()
def create_sample(extraction_result, temp_sample_id, job_id, worker_id, url, label=''):
    """
    Creates real sample using TemporarySample. If error while capturing web
    propagate it. Finally deletes TemporarySample.
    extraction_result should be [True, True] - otherwise chaining failed.
    """

    print 'a'
    extracted = all([x is True for x in extraction_result])
    temp_sample = TemporarySample.objects.get(id=temp_sample_id)

    # Checking if all previuos tasks succeeded.
    if extracted:
        job = Job.objects.get(id=job_id)
        worker = Worker.objects.get(id=worker_id)

        # Proper sample entry
        sample = Sample(
            job=job,
            url=url,
            text=temp_sample.text,
            screenshot=temp_sample.screenshot,
            added_by=worker,
            label=label
        )
        sample.save()
        print 'done a'
        return (extracted, sample.id)

    # We don't need this object any more.
    temp_sample.delete()

    print 'done a'
    return (extracted, None)
