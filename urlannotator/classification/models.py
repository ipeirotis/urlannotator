from django.db import models
from urlannotator.main.models import Job, Sample, LABEL_CHOICES
from tenclouds.django.jsonfield.fields import JSONField


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
    job = models.ForeignKey(Job, related_name="training_samples")
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=20, choices=LABEL_CHOICES)
