from django.db import models
from django.conf import settings
from urlannotator.main.models import Worker, Sample, LABEL_CHOICES, Job


class WorkerQualityVote(models.Model):
    worker = models.ForeignKey(Worker)
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES)
    added_on = models.DateField()
    is_valid = models.BooleanField(default=True)


class BeatTheMachineSamples(Sample):
    expected_output = models.CharField(max_length=10)
    classifier_output = models.CharField(max_length=10)
    error_ratio = models.DecimalField(default=0, decimal_places=5,
        max_digits=7)


class TagasaurisJobs(models.Model):
    urlannotator_job = models.OneToOneField(Job)
    sample_gathering_key = models.CharField(max_length=25)
    voting_key = models.CharField(max_length=25)
    beatthemachine_key = models.CharField(max_length=25, null=True, blank=True)
    sample_gathering_hit = models.CharField(max_length=25, null=True, blank=True)
    voting_hit = models.CharField(max_length=25, null=True, blank=True)

    def get_sample_gathering_url(self):
        """
            Returns URL under which Own Workforce can submit new samples.
        """
        return settings.TAGASAURIS_HIT_URL % self.sample_gathering_hit

    def get_voting_url(self):
        """
            Returns URL under which Own Workforce can vote on labels.
        """
        # TODO: Proper link
        return settings.TAGASAURIS_HIT_URL % self.sample_gathering_hit
