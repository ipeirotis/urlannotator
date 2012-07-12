from django.db import models
from urlannotator.main.models import Job
from tenclouds.django.jsonfield.fields import JSONField


class Classifier(models.Model):
    job = models.ForeignKey(Job)
    type = models.CharField(max_length=20)
    parameters = JSONField(max_length=100)


class Statistics(models.Model):
    pass
