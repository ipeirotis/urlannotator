from django.db import models
from urlannotator.main.models import Worker, Sample, LABEL_CHOICES


class WorkerQualityVote(models.Model):
    worker = models.ForeignKey(Worker)
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES)
    added_on = models.DateField()


class BeatTheMachineSamples(Sample):
    expected_output = models.CharField(max_length=10)
    classifier_output = models.CharField(max_length=10)
    error_ratio = models.DecimalField(default=0, decimal_places=5,
        max_digits=7)


class TagasaurisJobs(models.Model):
    urlannotator_job_id = models.CharField(max_length=25)
    sample_gatering_key = models.CharField(max_length=25)
    voting_key = models.CharField(max_length=25)
    beatthemachine_key = models.CharField(max_length=25, null=True, blank=True)
