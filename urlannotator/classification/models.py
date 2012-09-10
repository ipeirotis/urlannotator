import json
import urlparse

from tenclouds.django.jsonfield.fields import JSONField
from django.db import models
from django.db.models.signals import post_save

from urlannotator.main.models import Job, Sample, LABEL_CHOICES
from urlannotator.flow_control import send_event


class Classifier(models.Model):
    """
        Stores data required for system to instatiate correct classifier, and
        use it.
    """
    job = models.ForeignKey(Job)
    type = models.CharField(max_length=20)
    parameters = JSONField()
    main = models.BooleanField(default=True)


class Statistics(models.Model):
    pass


class PerformanceManager(models.Manager):
    def latest_for_job(self, job):
        """
            Returns performance for given job.
        """
        els = super(PerformanceManager, self).\
            get_query_set().filter(job=job).order_by('-date')
        if not els.count():
            return None

        return els[0]


class ClassifierPerformance(Statistics):
    """
        Keeps history of classifer performance for each job.
    """
    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    value = JSONField()

    objects = PerformanceManager()


class PerformancePerHourManager(models.Manager):
    def latest_for_job(self, job):
        """
            Returns performance statistic for given job.
        """
        els = super(PerformancePerHourManager, self).\
            get_query_set().filter(job=job).order_by('-date')
        if not els.count():
            return None

        return els[0]


class ClassifierPerformancePerHour(Statistics):
    """
        Keeps track of classifer performance for each job per hour.
    """
    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    value = JSONField()

    objects = PerformancePerHourManager()


def create_stats(sender, instance, created, **kwargs):
    """
        Creates a brand new statistics' entry for new job.
    """
    if created:
        val = json.dumps({})
        ClassifierPerformance.objects.create(job=instance, value=val)
        ClassifierPerformancePerHour.objects.create(job=instance, value=val)

post_save.connect(create_stats, sender=Job)


class TrainingSetManager(models.Manager):
    """
        Adds custom methods to TrainingSet model manager.
    """
    def newest_for_job(self, job):
        """
            Returns newest TrainingSet for given job
        """
        els = super(TrainingSetManager, self).get_query_set().filter(job=job).\
            order_by('-revision')
        if not els.count():
            return None

        return els[0]


class TrainingSet(models.Model):
    """
        A set of TrainingSamples used to train job's classifier.
    """
    job = models.ForeignKey(Job)
    revision = models.DateTimeField(auto_now_add=True)

    objects = TrainingSetManager()


class TrainingSample(models.Model):
    """
        A training sample used in TrainingSet to train job's classifier.
    """
    set = models.ForeignKey(TrainingSet, related_name="training_samples")
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=20, choices=LABEL_CHOICES)

# Classified sample source_type breakdown:
# owner - classify request from job owner. Source_val is irrevelant.
CLASS_SAMPLE_SOURCE_OWNER = 'owner'


class ClassifiedSampleManager(models.Manager):
    def _sanitize(self, args, kwargs):
        """
            Sanitizes information passed by users.
        """
        url = kwargs['url']
        if url:
            result = urlparse.urlsplit(url)
            if not result.scheme:
                kwargs['url'] = 'http://%s' % url

    def create_by_owner(self, *args, **kwargs):
        self._sanitize(args, kwargs)
        kwargs['source_type'] = CLASS_SAMPLE_SOURCE_OWNER
        kwargs['source_val'] = ''
        try:
            kwargs['sample'] = Sample.objects.get(
                job=kwargs['job'],
                url=kwargs['url']
            )
        except Sample.DoesNotExist:
            pass

        classified_sample = self.create(**kwargs)
        # If sample exists, step immediately to classification
        if 'sample' in kwargs:
            send_event('EventNewClassifySample',
                sample_id=classified_sample.id)
        else:
            Sample.objects.create_by_owner(
                job_id=kwargs['job'].id,
                url=kwargs['url'],
                create_classified=False,
            )

        return classified_sample

# Classified samples' status breakdown:
# PENDING - The sample is being created or classified. If
#           ClassifiedSample.sample is not none, the sample is being classified
# SUCCESS - The sample has been created and classified.
CLASSIFIED_SAMPLE_SUCCESS = 'SUCCESS'
CLASSIFIED_SAMPLE_PENDING = 'PENDING'


class ClassifiedSample(models.Model):
    """
        A sample classification request was made for. The sample field is set
        when corresponding sample is created.
    """
    sample = models.ForeignKey(Sample, blank=True, null=True)
    url = models.URLField()
    job = models.ForeignKey(Job)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES, blank=False)
    source_type = models.CharField(max_length=100, blank=False)
    source_val = models.CharField(max_length=100, blank=True, null=True)
    label_probability = JSONField()

    objects = ClassifiedSampleManager()

    def get_status(self):
        '''
            Returns current classification status.
        '''
        if self.sample and self.label:
            return CLASSIFIED_SAMPLE_SUCCESS
        return CLASSIFIED_SAMPLE_PENDING

    def is_pending(self):
        return self.get_status() == CLASSIFIED_SAMPLE_PENDING

    def is_successful(self):
        return self.get_status() == CLASSIFIED_SAMPLE_SUCCESS

    def get_source_worker(self):
        """
            Returns a worker who has sent this sample.
        """
        return Sample.get_worker(
            source_type=self.source_type,
            source_val=self.source_val,
        )
