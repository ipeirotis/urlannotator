import datetime
import random

from django.conf import settings
from celery import group, chain

from urlannotator.classification.models import TrainingSet
from urlannotator.classification.factories import classifier_factory
from urlannotator.main.models import Job, Sample, FillSample, LABEL_NO
from urlannotator.main.tasks import (web_content_extraction,
    web_screenshot_extraction, create_sample, create_classify_sample,
    copy_sample_to_job)
from urlannotator.tools.utils import setting

import logging
log = logging.getLogger(__name__)


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

        is_btm = kwargs.get('btm_sample', False)

        # Create a new sample for the job from existing one (if job is
        # missing it). If the job has that sample, create only classified.
        if samples:
            job_samples = samples.filter(job=job, btm_sample=is_btm)
            if is_btm:
                if job_samples:
                    return job_samples[0].id
                return copy_sample_to_job.s(samples[0].id, job.id,
                    label=label, btm_sample=True, *args, **kwargs
                    ).apply_async()
            else:
                if job_samples:
                    return create_classify_sample.delay(
                        result=(True, job_samples[0].id),
                        label=label,
                        *args, **kwargs
                    )
                return (
                    copy_sample_to_job.s(samples[0].id, job.id, label=label,
                        *args, **kwargs)
                    |
                    create_classify_sample.s(label=label, *args, **kwargs)
                ).apply_async()

        sample = Sample.objects.create(url=url, job=job)

        # Groups screenshot and content extraction. On both success proceeds
        # to sample creation. Used Celery Chords.
        return chain(
            group(
                web_screenshot_extraction.s(sample_id=sample.id, url=url),
                web_content_extraction.s(sample_id=sample.id, url=url)
            ),
            create_sample.s(
                sample_id=sample.id,
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

        fillers = list(FillSample.objects.all())
        random.shuffle(fillers)
        fillers = fillers[:min(job.no_of_urls, len(fillers))]
        for filler in fillers:
            job.gold_samples.append({
                'url': filler.url,
                'label': LABEL_NO,
            })
        job.save()

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
        TrainingSet.objects.create(job=job)
        job.set_training_set_created()

    def create_classifier(self, job):
        """
            Creates classifier entry with type equal to JOB_DEFAULT_CLASSIFIER.
        """
        classifier_prefix = '%s-' % setting('SITE_URL', '127.0.0.1')
        classifier_factory.initialize_classifier(
            job_id=job.id,
            classifier_name=settings.JOB_DEFAULT_CLASSIFIER,
            prefix=classifier_prefix,
        )

    def init_quality(self, job_id):
        Job.objects.filter(id=job_id).update(
            votes_storage=settings.VOTES_STORAGE,
            quality_algorithm=settings.QUALITY_ALGORITHM,
        )

    def initialize_job(self, job_id, *args, **kwargs):
        """
            Initializes new job's elements from given job entry's id.
        """

        job = Job.objects.get(id=job_id)

        self.create_training_set(job)
        self.create_classifier(job)
        self.prepare_gold_samples(job.id)
        self.classify_urls(job.id)
        self.init_quality(job_id)

        job.update_cache()
