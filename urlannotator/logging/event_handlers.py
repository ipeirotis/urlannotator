from celery import task

from urlannotator.main.models import Job, Sample, GoldSample
from urlannotator.classification.models import ClassifiedSample
from urlannotator.logging.models import LogEntry, LongActionEntry
from urlannotator.logging.settings import (
    LOG_TYPE_JOB_INIT_START,
    LOG_TYPE_JOB_INIT_DONE,
    LOG_TYPE_NEW_SAMPLE_START,
    LOG_TYPE_NEW_GOLD_SAMPLE,
    LOG_TYPE_NEW_SAMPLE_DONE,
    LOG_TYPE_CLASS_TRAIN_START,
    LOG_TYPE_CLASS_TRAIN_DONE,
    LOG_TYPE_SAMPLE_CLASSIFIED,

    LONG_ACTION_TRAINING,
)


@task(ignore_result=True)
def log_new_job(job_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    LogEntry.objects.log(
        log_type=LOG_TYPE_JOB_INIT_START,
        job=job,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_new_job_done(job_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    LogEntry.objects.log(
        log_type=LOG_TYPE_JOB_INIT_DONE,
        job=job,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_new_sample_start(job_id, url, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    params = {
        'sample_url': url,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_NEW_SAMPLE_START,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_sample_done(job_id, sample_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    sample = Sample.objects.get(id=sample_id)
    params = {
        'sample_id': sample_id,
        'sample_url': sample.url,
        'sample_screenshot': sample.screenshot,
    }

    LogEntry.objects.log(
        log_type=LOG_TYPE_NEW_SAMPLE_DONE,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_gold_sample_done(job_id, gold_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    gold = GoldSample.objects.get(id=gold_id)
    params = {
        'gold_sample': gold_id,
        'gold_url': gold.sample.url,
        'gold_label': gold.label,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_NEW_GOLD_SAMPLE,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_classifier_trained(job_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    LogEntry.objects.log(
        log_type=LOG_TYPE_CLASS_TRAIN_DONE,
        job=job,
        *args, **kwargs
    )
    LongActionEntry.objects.finish_action(
        job=job,
        action_type=LONG_ACTION_TRAINING,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_classifier_train_start(job_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    LogEntry.objects.log(
        log_type=LOG_TYPE_CLASS_TRAIN_START,
        job=job,
        *args, **kwargs
    )
    LongActionEntry.objects.start_action(
        job=job,
        action_type=LONG_ACTION_TRAINING,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_sample_classified(job_id, class_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    class_sample = ClassifiedSample.objects.get(id=class_id)
    params = {
        'class_id': class_sample.id,
        'sample_id': class_sample.sample_id,
        'class_url': class_sample.url,
        'class_label': class_sample.label,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_SAMPLE_CLASSIFIED,
        job=job,
        params=params,
        *args, **kwargs
    )

FLOW_DEFINITIONS = [
    (r'^EventNewRawSample$', log_new_sample_start),
    (r'^EventNewSample$', log_sample_done),
    (r'^EventNewJobInitialization$', log_new_job),
    (r'^EventNewGoldSample$', log_gold_sample_done),
    (r'^EventNewJobInitializationDone$', log_new_job_done),
    (r'^EventClassifierTrained$', log_classifier_trained),
    (r'^EventSampleClassified$', log_sample_classified),
    (r'^EventTrainingSetCompleted$', log_classifier_train_start),
]
