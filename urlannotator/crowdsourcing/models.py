from django.db import models
from django.conf import settings

from urlannotator.main.models import (Worker, Sample, LABEL_CHOICES, Job,
    WorkerJobAssociation, SAMPLE_TAGASAURIS_WORKER)
from urlannotator.classification.models import (ClassifiedSample,
    ClassifiedSampleManager)
from urlannotator.flow_control import send_event


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
        self._sanitize(args, kwargs)
        kwargs['source_type'] = SAMPLE_TAGASAURIS_WORKER
        kwargs['source_val'] = kwargs['worker_id']
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
            Sample.objects.create_by_worker(
                job_id=kwargs['job'].id,
                url=kwargs['url'],
                source_val=kwargs['source_val'],
                create_classified=False,
            )

        return classified_sample


class BeatTheMachineSample(ClassifiedSample):
    # BTM status and description/points mapping
    BTM_PENDING = 0
    BTM_KNOWN = 1

    BTM_STATUS = (
        (BTM_PENDING, "Pending"),
        (BTM_KNOWN,  "Known"),
    )

    BTM_POINTS = {
        BTM_PENDING: 0,
        BTM_KNOWN: 0,
    }

    expected_output = models.CharField(max_length=10, choices=LABEL_CHOICES)
    btm_status = models.IntegerField(default=BTM_PENDING, choices=BTM_STATUS)
    points = models.IntegerField(default=0)

    objects = BeatTheMachineSampleManager()

    @property
    def confidence(self):
        return self.label_probability[self.label]

    def updateBTMStatus(self, save=True):
        status = self.calculate_status(
            matched=self.labels_matched(),
            confidence=self.confidence)

        self.btm_status = status
        self.points = self.BTM_POINTS[status]

        if save:
            self.save()

    def labels_matched(self):
        return self.expected_output.lower() == self.label.lower()

    def btm_status_mapping():
        return ""

    @classmethod
    def calculate_status(cls, matched, confidence):
        return cls.BTM_KNOWN


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


class TroiaJob(models.Model):
    job = models.OneToOneField(Job)
    troia_id = models.CharField(max_length=64)
