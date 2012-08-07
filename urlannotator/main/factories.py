import datetime
from django.conf import settings
from celery import group, chain

from urlannotator.classification.models import TrainingSet, Classifier
from urlannotator.classification.factories import classifier_factory
from urlannotator.main.models import TemporarySample, Job, Sample
from urlannotator.main.tasks import (web_content_extraction,
    web_screenshot_extraction, create_sample, create_classify_sample,
    copy_sample_to_job)


class SampleFactory(object):
    """
    Gets:
        Job, worker & url.
    Result:
        None
    """

    def new_sample(self, job_id, url='', text=None, label=None,
            *args, **kwargs):
        """
        Produce new sample and starts tasks for screen and text extraction.
        Label argument is passed only when we create GoldSample.
        """

        # Check if sample with given url exists across the system
        samples = Sample.objects.filter(url=url)
        job = Job.objects.get(id=job_id)

        # Create a new sample for the job from existing one (if job is
        # missing it). If the job has that sample, create only classified.
        if samples:
            job_samples = samples.filter(job=job)
            if job_samples:
                return create_classify_sample.delay(
                    job_samples[0].id, label=label, *args, **kwargs
                )
            return (
                copy_sample_to_job.s(samples[0].id, job.id, label=label,
                    *args, **kwargs)
                |
                create_classify_sample.s(label=label, *args, **kwargs)
            ).apply_async()

        temp_sample = TemporarySample(url=url)
        temp_sample.save()

        # Groups screensot and content extraction. On both success proceeds
        # to sample creation. Used Celery Chords.
        return chain(group([
            web_screenshot_extraction.s(temp_sample.id, url=url),
            web_content_extraction.s(temp_sample.id, url=url)]),
            create_sample.s(
                temp_sample_id=temp_sample.id,
                job_id=job_id,
                url=url,
                label=label,
                *args, **kwargs
            ),
            create_classify_sample.s(
                label=label,
                *args, **kwargs
            )
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

        if not job.gold_samples:
            job.set_gold_samples_done()
        else:
            for gold_sample in job.gold_samples:
                Sample.objects.create_by_owner(
                    job_id=job_id,
                    url=gold_sample['url'],
                    label=gold_sample['label']
                )

    def classify_urls(self, job_id):
        """
            Classifies all urls provided on job creation.
        """

        job = Job.objects.get(id=job_id)

        for sample_url in job.classify_urls:
            Sample.objects.create_by_owner(
                job_id=job_id,
                url=sample_url
            )

    def create_training_set(self, job):
        """
            Creates first training set that will consist of gold samples
        """
        TrainingSet(job=job).save()
        job.set_training_set_created()

    def create_classifier(self, job):
        """
            Creates classifier entry with type equal to JOB_DEFAULT_CLASSIFIER.
        """
        Classifier(
            job=job,
            type=settings.JOB_DEFAULT_CLASSIFIER,
            parameters=''
        ).save()
        classifier_factory.initialize_classifier(
            job.id,
            settings.JOB_DEFAULT_CLASSIFIER
        )

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
