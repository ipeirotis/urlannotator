from django.db import models
from django.conf import settings

from urlannotator.main.models import (Worker, Sample, LABEL_CHOICES, Job,
    WorkerJobAssociation)
from urlannotator.classification.models import (ClassifiedSample,
    ClassifiedSampleManager)


class WorkerQualityVoteManager(models.Manager):
    def new_vote(self, *args, **kwargs):
        WorkerJobAssociation.objects.associate(
            job=kwargs['sample'].job,
            worker=kwargs['worker'],
        )
        return self.create(**kwargs)


class WorkerQualityVote(models.Model):
    worker = models.ForeignKey(Worker)
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES)
    added_on = models.DateField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)
    is_new = models.BooleanField(default=True)

    objects = WorkerQualityVoteManager()

    class Meta:
        unique_together = ['worker', 'sample']


class BeatTheMachineSampleManager(ClassifiedSampleManager):
    def create_by_worker(self, *args, **kwargs):
        return self.create_by_owner(*args, **kwargs)


class BeatTheMachineSample(ClassifiedSample):
    worker = models.ForeignKey(Worker)
    expected_output = models.CharField(max_length=10, choices=LABEL_CHOICES)
    error_ratio = models.DecimalField(default=0, decimal_places=5,
        max_digits=7)

    objects = BeatTheMachineSampleManager()

    def labels_matched(self):
        return self.expected_output.lower() == self.label.lower()


class TagasaurisJobs(models.Model):
    urlannotator_job = models.OneToOneField(Job)
    sample_gathering_key = models.CharField(max_length=25)
    voting_key = models.CharField(max_length=25, null=True, blank=True)
    beatthemachine_key = models.CharField(max_length=25, null=True, blank=True)
    sample_gathering_hit = models.CharField(max_length=25, null=True,
        blank=True)
    voting_hit = models.CharField(max_length=25, null=True, blank=True)
    beatthemachine_hit = models.CharField(max_length=25, null=True, blank=True)

    def _get_job_url(self, task):
        """ Returns URL under which Own Workforce can perform given task.
        """
        if task is not None:
            return settings.TAGASAURIS_HIT_URL % task

        return ''

    def get_sample_gathering_url(self):
        return self._get_job_url(self.sample_gathering_hit)

    def get_voting_url(self):
        return self._get_job_url(self.voting_hit)

    def get_beatthemachine_url(self):
        return self._get_job_url(self.beatthemachine_hit)


class SampleMapping(models.Model):
    TAGASAURIS = 'TAGASAURIS'
    CROWDSOURCING_CHOICES = (
        (TAGASAURIS, 'Tagasauris'),
    )

    sample = models.ForeignKey(Sample)
    external_id = models.CharField(max_length=25)
    crowscourcing_type = models.CharField(max_length=20,
        choices=CROWDSOURCING_CHOICES)
