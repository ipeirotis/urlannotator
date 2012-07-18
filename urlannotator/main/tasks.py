from celery import task

from urlannotator.main.models import TemporarySample, Sample, Job, Worker
from urlannotator.tools.web_extractors import get_web_text, get_web_screenshot
from urlannotator.flow_control.event_system import event_bus


@task()
def web_content_extraction(sample_id, url=None):
    """ Links/lynx required. Generates html output from those browsers.
    """
    if url is None:
        url = TemporarySample.objects.get(id=sample_id).url

    text = get_web_text(url)
    TemporarySample.objects.filter(id=sample_id).update(text=text)

    return True


@task()
def web_screenshot_extraction(sample_id, url=None):
    """ CutyCapt required. Generates html output from those browsers.
    """
    if url is None:
        url = TemporarySample.objects.get(id=sample_id).url

    try:
        screenshot = get_web_screenshot(url)
    except Exception, e:
        raise web_content_extraction.retry(exc=e, countdown=60)

    TemporarySample.objects.filter(id=sample_id).update(
        screenshot=screenshot)

    return True


@task()
def create_sample(extraction_result, temp_sample_id, job_id, worker_id, url,
    label='', silent=False):
    """
    Creates real sample using TemporarySample. If error while capturing web
    propagate it. Finally deletes TemporarySample.
    extraction_result should be [True, True] - otherwise chaining failed.
    """

    sample_id = None
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
        sample_id = sample.id

        if not silent:
            # Sample created sucesfully - pushing event.
            event_bus.delay("EventNewSample", sample_id)

    # We don't need this object any more.
    temp_sample.delete()

    return (extracted, sample_id)
