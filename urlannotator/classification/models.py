from django.db import models
from urlannotator.main.models import Job, Sample, LABEL_CHOICES
from tenclouds.django.jsonfield.fields import JSONField


class Classifier(models.Model):
    job = models.ForeignKey(Job)
    type = models.CharField(max_length=20)
    parameters = JSONField()


class Statistics(models.Model):
    pass


class TrainingSet(models.Model):
    job = models.ForeignKey(Job)
    revision = models.DateTimeField(auto_now_add=True)


class TrainingSample(models.Model):
    job = models.ForeignKey(Job, related_name="training_samples")
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=20, choices=LABEL_CHOICES)
