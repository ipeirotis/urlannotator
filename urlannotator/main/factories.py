import datetime
from django.conf import settings
from celery import group

from urlannotator.classification.models import TrainingSet, Classifier
from urlannotator.main.models import TemporarySample, Job, Worker
from urlannotator.main.tasks import (web_content_extraction,
    web_screenshot_extraction, create_sample, create_classify_sample)
from urlannotator.flow_control import send_event


class SampleFactory(object):
    """
    Gets:
        Job, worker & url.
    Result:
        None
    """

    def new_sample(self, job_id, worker_id, url='', text=None, label=None,
            *args, **kwargs):
        """
        Produce new sample and starts tasks for screen and text extraction.
        Label argument is passed only when we create GoldenSample.
        """

        # Injecting administrator classification request (no web extraction
        # needed)
        if text is not None:
            return create_classify_sample.delay(job_id, worker_id, url, text,
                label, *args, **kwargs)

        # Ordinary classification or golden sample.
        else:
            temp_sample = TemporarySample()
            temp_sample.save()

            # Groups screensot and content extraction. On both success proceeds
            # to sample creation. Used Celery Chords.
            return (group([
                web_screenshot_extraction.s(temp_sample.id, url=url),
                web_content_extraction.s(temp_sample.id, url=url)])
                |
                create_sample.s(temp_sample.id, job_id, worker_id, url, label,
                    *args, **kwargs)
            ).apply_async(
                expires=datetime.datetime.now() + datetime.timedelta(days=1)
            )


class JobFactory(object):
    """
    Gets:
        Job id.
    Result:
        None
    """

    def prepare_gold_samples(self, job_id):
        """
            Creates gold samples for given job.
        """
        job = Job.objects.get(id=job_id)

        # FIXME: fake worker
        w = Worker()
        w.save()

        if not job.gold_samples:
            job.status = 1
            job.save()
        else:
            for gold_sample in job.gold_samples:
                send_event('EventNewRawSample', job_id, w.id,
                    gold_sample['url'], label=gold_sample['label'])
        return None

    def classify_urls(self, job_id):
        """
            Classifies all urls provided on job creation.
        """

        job = Job.objects.get(id=job_id)

        # FIXME: fake worker
        w = Worker()
        w.save()

        for sample in job.classify_urls:
            send_event('EventNewRawSample', job_id, w.id, sample)
        return None

    def create_training_set(self, job):
        """
            Creates first training set that will consist of gold samples
        """
        TrainingSet(job=job).save()

    def create_classifier(self, job):
        """
            Creates classifier entry with type equal to JOB_DEFAULT_CLASSIFIER.
        """
        Classifier(
            job=job,
            type=settings.JOB_DEFAULT_CLASSIFIER,
            parameters=''
        ).save()

    def initialize_job(self, job_id, *args, **kwargs):
        """
            Initializes new job's elements from given job entry's id.
        """

        # TODO: Add remaining elements of a job
        job = Job.objects.get(id=job_id)

        self.create_training_set(job)
        self.create_classifier(job)
        self.prepare_gold_samples(job.id)
        self.classify_urls(job.id)
