from celery import task
from celery.task import current

from urlannotator.main.models import (TemporarySample, Sample, GoldSample, Job,
    Worker)
from urlannotator.tools.web_extractors import get_web_text, get_web_screenshot
from urlannotator.flow_control import send_event


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
        current.retry(exc=e, countdown=min(60 * 2 ** current.request.retries,
            60 * 60 * 24))

    TemporarySample.objects.filter(id=sample_id).update(
        screenshot=screenshot)

    return True


@task()
def create_sample(extraction_result, temp_sample_id, job_id, worker_id, url,
    label=None, silent=False):
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
            added_by=worker
        )
        sample.save()
        sample_id = sample.id

        if not silent:
            # Golden sample
            if label is not None:
                # GoldSample created sucesfully - pushing event.
                gold = GoldSample(
                    sample=sample,
                    label=label
                )
                gold.save()
                send_event("EventNewGoldSample", gold.id)

            # Ordinary sample
            else:
                # Sample created sucesfully - pushing event.
                send_event("EventNewSample", sample_id)

    # We don't need this object any more.
    temp_sample.delete()

    return (extracted, sample_id)


@task()
def create_classify_sample(job_id, worker_id, url, text, label=None,
        silent=False):
    """
    Creates sample for job administrator (not workers) therfore we don't need
    web extraction.
    """

    job = Job.objects.get(id=job_id)
    worker = Worker.objects.get(id=worker_id)

    # Proper sample entry
    sample = Sample(
        job=job,
        url=url,
        text=text,
        added_by=worker
    )
    sample.save()

    # Sample created sucesfully - pushing event.
    send_event("EventNewClassifySample", sample.id)

    return (True, sample.id)
