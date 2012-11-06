from celery import task
from django.conf import settings

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
    LOG_TYPE_SAMPLE_SCREENSHOT_DONE,
    LOG_TYPE_SAMPLE_TEXT_DONE,
    LOG_TYPE_SAMPLE_SCREENSHOT_FAIL,
    LOG_TYPE_SAMPLE_TEXT_FAIL,
    LOG_TYPE_CLASSIFIER_TRAINING_ERROR,
    LOG_TYPE_CLASSIFIER_FATAL_TRAINING_ERROR,

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
        'sample_screenshot': sample.get_small_thumbnail_url(),
        'sample_image': sample.get_small_thumbnail_url(),
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
        'sample_image': gold.sample.get_small_thumbnail_url(),
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
        'sample_image': class_sample.sample.get_small_thumbnail_url(),
        'class_label': class_sample.label,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_SAMPLE_CLASSIFIED,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_btm_sample_classified(job_id, btm_id, *args, **kwargs):
    # TODO: Add info about btm status. Ignore expected labels; show important
    # ones.
    pass


@task(ignore_result=True)
def log_sample_screenshot_done(sample_id, sample_url, job_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    params = {
        'sample_id': sample_id,
        'sample_url': sample_url,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_SAMPLE_SCREENSHOT_DONE,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_sample_text_done(sample_id, sample_url, job_id, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    params = {
        'sample_id': sample_id,
        'sample_url': sample_url,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_SAMPLE_TEXT_DONE,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_sample_text_fail(sample_id, error_code, sample_url, job_id,
        *args, **kwargs):
    job = Job.objects.get(id=job_id)
    params = {
        'sample_id': sample_id,
        'sample_url': sample_url,
        'error_code': error_code
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_SAMPLE_TEXT_FAIL,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_sample_screenshot_fail(sample_id, error_code, sample_url, job_id,
        *args, **kwargs):
    job = Job.objects.get(id=job_id)
    params = {
        'sample_id': sample_id,
        'sample_url': sample_url,
        'error_code': error_code,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_SAMPLE_SCREENSHOT_FAIL,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_classifier_train_error(job_id, message, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    params = {
        'error_message': message,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_CLASSIFIER_TRAINING_ERROR,
        job=job,
        params=params,
        *args, **kwargs
    )


@task(ignore_result=True)
def log_classifier_critical_train_error(job_id, message, *args, **kwargs):
    job = Job.objects.get(id=job_id)
    params = {
        'error_message': message,
    }
    LogEntry.objects.log(
        log_type=LOG_TYPE_CLASSIFIER_FATAL_TRAINING_ERROR,
        job=job,
        params=params,
        *args, **kwargs
    )
    LongActionEntry.objects.finish_action(
        job=job,
        action_type=LONG_ACTION_TRAINING,
        *args, **kwargs
    )

FLOW_DEFINITIONS = [
    (r'^EventNewRawSample$', log_new_sample_start, settings.CELERY_REALTIME_QUEUE),
    (r'^EventNewSample$', log_sample_done, settings.CELERY_REALTIME_QUEUE),
    (r'^EventNewJobInitialization$', log_new_job, settings.CELERY_REALTIME_QUEUE),
    (r'^EventNewGoldSample$', log_gold_sample_done, settings.CELERY_REALTIME_QUEUE),
    (r'^EventNewJobInitializationDone$', log_new_job_done, settings.CELERY_REALTIME_QUEUE),
    (r'^EventClassifierTrained$', log_classifier_trained, settings.CELERY_REALTIME_QUEUE),
    (r'^EventSampleClassified$', log_sample_classified, settings.CELERY_REALTIME_QUEUE),
    (r'^EventSampleBTM$', log_btm_sample_classified, settings.CELERY_REALTIME_QUEUE),
    (r'^EventTrainingSetCompleted$', log_classifier_train_start, settings.CELERY_REALTIME_QUEUE),
    (r'^EventSampleScreenshotDone$', log_sample_screenshot_done, settings.CELERY_REALTIME_QUEUE),
    (r'^EventSampleScreenshotFail$', log_sample_screenshot_fail, settings.CELERY_REALTIME_QUEUE),
    (r'^EventSampleContentDone$', log_sample_text_done, settings.CELERY_REALTIME_QUEUE),
    (r'^EventClassifierTrainError$', log_classifier_train_error, settings.CELERY_REALTIME_QUEUE),
    (r'^EventClassifierCriticalTrainError$', log_classifier_critical_train_error, settings.CELERY_REALTIME_QUEUE),
]
