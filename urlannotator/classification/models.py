from tenclouds.django.jsonfield.fields import JSONField
from django.db import models
from django.db.models.signals import post_save

from urlannotator.main.models import Job, Sample, LABEL_CHOICES


class Classifier(models.Model):
    """
        Stores data required for system to instatiate correct classifier, and
        use it.
    """
    job = models.ForeignKey(Job)
    type = models.CharField(max_length=20)
    parameters = JSONField()


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
    value = models.IntegerField(default=0)

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
    value = models.IntegerField(default=0)
    delta = models.IntegerField(default=0)

    objects = PerformancePerHourManager()


def create_stats(sender, instance, created, **kwargs):
    """
        Creates a brand new statistics' entry for new job.
    """
    if created:
        ClassifierPerformance.objects.create(job=instance, value=0)
        ClassifierPerformancePerHour.objects.create(job=instance, value=0)

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
