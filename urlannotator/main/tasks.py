import subprocess

from celery import task
from celery.task import current
from django.db import DatabaseError, IntegrityError

from urlannotator.classification.models import ClassifiedSample
from urlannotator.main.models import Sample, GoldSample, Job
from urlannotator.tools.web_extractors import get_web_text, get_web_screenshot
from urlannotator.flow_control import send_event
from urlannotator.tools.webkit2png import BadURLException


@task()
def web_content_extraction(sample_id, url=None, *args, **kwargs):
    """ Links/lynx required. Generates html output from those browsers.
    """
    if url is None:
        url = Sample.objects.get(id=sample_id).url

    try:
        text = get_web_text(url)
    except subprocess.CalledProcessError, e:
        # Something wrong has happened to links. Couldn't find documentation on
        # error codes - assume bad stuff has happened that retrying won't fix.
        send_event(
            'EventSampleContentFail',
            sample_id=sample_id,
            error_code=e.returncode
        )
        return False

    Sample.objects.filter(id=sample_id).update(text=text)
    send_event(
        "EventSampleContentDone",
        sample_id=sample_id,
    )
    return True


@task()
def web_screenshot_extraction(sample_id, url=None, *args, **kwargs):
    """ Generates html output from those browsers.
    """
    if url is None:
        url = Sample.objects.get(id=sample_id).url

    try:
        screenshot = get_web_screenshot(url)
    except BadURLException, e:
        send_event(
            "EventSampleScreenshotFail",
            sample_id=sample_id,
            error_code=e.status_code,
        )
        return False
    except Exception, e:
        current.retry(exc=e, countdown=min(60 * 2 ** current.request.retries,
            60 * 60 * 24))

    Sample.objects.filter(id=sample_id).update(screenshot=screenshot)

    send_event(
        "EventSampleScreenshotDone",
        sample_id=sample_id,
    )
    return True


@task()
def create_sample(extraction_result, sample_id, job_id, url,
    source_type, source_val='', label=None, silent=False, *args, **kwargs):
    """
    If error while capturing web propagate it. Finally deletes TemporarySample.
    extraction_result should be [True, True] - otherwise chaining failed.
    """

    extracted = all([x is True for x in extraction_result])

    # Checking if all previous tasks succeeded.
    if extracted:
        job = Job.objects.get(id=job_id)

        # Proper sample entry
        Sample.objects.filter(id=sample_id).update(
            source_type=source_type,
            source_val=source_val
        )
        sample = Sample.objects.get(id=sample_id)

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
                send_event(
                    "EventNewSample",
                    job_id=job.id,
                    sample_id=sample_id,
                )

        # Celery Chain workaround until celery works fine with groups
        # and chains
        create_classify_sample.delay(
            sample_id=sample_id,
            label=label,
            source_type=source_type,
            source_val=source_val,
            job_id=job_id,
            url=url,
            *args, **kwargs
        )
    else:
        # Extraction failed, cleanup.
        Sample.objects.filter(id=sample_id).delete()

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

    # Don't classify already classified samples
    if label:
        return sample_id

    if create_classified:
        try:
            sample = Sample.objects.get(id=sample_id)

            if not label:
                label = ''

            # Proper sample entry
            class_sample = ClassifiedSample.objects.create(
                job=sample.job,
                url=sample.url,
                sample=sample,
                label=label,
                source_type=source_type,
                source_val=source_val,
            )

            # Sample created sucesfully - pushing event.
            send_event(
                "EventNewClassifySample",
                sample_id=class_sample.id,
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

        send_event(
            "EventSampleScreenshotDone",
            sample_id=new_sample.id,
        )
        send_event(
            "EventSampleContentDone",
            sample_id=new_sample.id,
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
            send_event(
                "EventNewSample",
                job_id=job.id,
                sample_id=new_sample.id,
            )

    except IntegrityError:
        # Such sample has been created in the mean time, dont do anything
        return Sample.objects.get(job=job, url=old_sample.url).id
    except DatabaseError, e:
        # Retry process on db error, such as 'Database is locked'
        copy_sample_to_job.retry(exc=e,
            countdown=min(60 * 2 ** current.request.retries, 60 * 60 * 24))

    return new_sample.id
