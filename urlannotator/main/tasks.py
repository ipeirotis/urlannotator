from celery import task
from celery.task import current
from django.db import DatabaseError, IntegrityError

from urlannotator.classification.models import ClassifiedSample
from urlannotator.main.models import (TemporarySample, Sample, GoldSample, Job)
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
def create_sample(extraction_result, temp_sample_id, job_id, url,
    source_type, source_val='', label=None, silent=False, *args, **kwargs):
    """
    Creates real sample using TemporarySample. If error while capturing web
    propagate it. Finally deletes TemporarySample.
    extraction_result should be [True, True] - otherwise chaining failed.
    """

    sample_id = None
    extracted = all([x is True for x in extraction_result])
    temp_sample = TemporarySample.objects.get(id=temp_sample_id)

    # Checking if all previous tasks succeeded.
    if extracted:
        job = Job.objects.get(id=job_id)

        # Proper sample entry
        sample = Sample(
            job=job,
            url=url,
            text=temp_sample.text,
            screenshot=temp_sample.screenshot,
            source_type=source_type,
            source_val=source_val
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
                send_event(
                    "EventNewGoldSample",
                    job_id=job.id,
                    gold_id=gold.id,
                )

            # Ordinary sample
            else:
                # Sample created sucesfully - pushing event.
                send_event("EventNewSample", sample_id)

    # We don't need this object any more.
    temp_sample.delete()

    return (extracted, sample_id)


@task()
def create_classify_sample(sample_id, source_type, create_classified=True,
    label='', source_val='', *args, **kwargs):
    """
    Creates classified sample from existing sample, therefore we don't need
    web extraction.
    """

    # We are given a tuple with create_sample results
    if isinstance(sample_id, tuple):
        sample_id = sample_id[1]

    if create_classified:
        try:
            sample = Sample.objects.get(id=sample_id)

            if not label:
                label = ''

            # Proper sample entry
            class_sample = ClassifiedSample(
                job=sample.job,
                url=sample.url,
                sample=sample,
                label=label,
                source_type=source_type,
                source_val=source_val
            )

            class_sample.save()

            # Sample created sucesfully - pushing event.
            send_event(
                "EventNewClassifySample",
                class_sample.id,
            )

        except DatabaseError, e:
            # Retry process on db error, such as 'Database is locked'
            create_classify_sample.retry(exc=e,
                countdown=min(60 * 2 ** current.request.retries, 60 * 60 * 24))

    return sample_id


@task()
def copy_sample_to_job(sample_id, job_id, source_type, label='', source_val='',
    *args, **kwargs):
    try:
        old_sample = Sample.objects.get(id=sample_id)
        job = Job.objects.get(id=job_id)
        new_sample = Sample.objects.create(
            job=job,
            url=old_sample.url,
            text=old_sample.text,
            screenshot=old_sample.screenshot,
            source_type=source_type,
            source_val=source_val
        )

        # Golden sample
        if label is not None:
            # GoldSample created sucesfully - pushing event.
            gold = GoldSample(
                sample=new_sample,
                label=label
            )
            gold.save()
            send_event(
                "EventNewGoldSample",
                job_id=job.id,
                gold_id=gold.id,
            )

        # Ordinary sample
        else:
            # Sample created sucesfully - pushing event.
            send_event("EventNewSample", new_sample.id)

    except IntegrityError:
        # Such sample has been created in the mean time, dont do anything
        return Sample.objects.get(job=job, url=old_sample.url).id
    except DatabaseError, e:
        # Retry process on db error, such as 'Database is locked'
        copy_sample_to_job.retry(exc=e,
            countdown=min(60 * 2 ** current.request.retries, 60 * 60 * 24))

    return new_sample.id
