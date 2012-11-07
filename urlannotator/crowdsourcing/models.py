from django.db import models
from django.conf import settings

from urlannotator.main.models import (Worker, Sample, LABEL_CHOICES, Job,
    WorkerJobAssociation, SAMPLE_TAGASAURIS_WORKER)
from urlannotator.classification.models import ClassifiedSampleCore
from urlannotator.flow_control import send_event
from urlannotator.tools.utils import sanitize_url

import logging
log = logging.getLogger(__name__)


class WorkerQualityVoteManager(models.Manager):
    def new_vote(self, *args, **kwargs):
        WorkerJobAssociation.objects.associate(
            job=kwargs['sample'].job,
            worker=kwargs['worker'],
        )

        send_event(
            'EventNewVoteAdded',
            worker_id=kwargs['worker'].id,
            sample_id=kwargs['sample'].id,
        )
        return self.create(**kwargs)

    def new_btm_vote(self, *args, **kwargs):
        WorkerJobAssociation.objects.associate(
            job=kwargs['sample'].job,
            worker=kwargs['worker'],
        )
        kwargs['btm_vote'] = True
        return self.create(**kwargs)


class WorkerQualityVote(models.Model):
    worker = models.ForeignKey(Worker)
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES)
    added_on = models.DateField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)
    is_new = models.BooleanField(default=True)
    btm_vote = models.BooleanField(default=False)

    objects = WorkerQualityVoteManager()

    class Meta:
        unique_together = ['worker', 'sample']


class BeatTheMachineSampleManager(models.Manager):
    def create_by_worker(self, *args, **kwargs):
        kwargs['url'] = sanitize_url(kwargs['url'])
        kwargs['source_type'] = SAMPLE_TAGASAURIS_WORKER
        kwargs['source_val'] = kwargs['worker_id']
        del kwargs['worker_id']
        try:
            kwargs['sample'] = Sample.objects.get(
                job=kwargs['job'],
                url=kwargs['url']
            )
        except Sample.DoesNotExist:
            pass

        btm_sample = self.create(**kwargs)
        # If sample exists, step immediately to classification
        if 'sample' in kwargs:
            send_event('EventNewClassifyBTMSample',
                sample_id=btm_sample.id)
        else:
            Sample.objects.create_by_btm(
                job_id=kwargs['job'].id,
                url=kwargs['url'],
                source_val=kwargs['source_val'],
                create_classified=False,
            )

        return btm_sample


class BeatTheMachineSample(ClassifiedSampleCore):
    # BTM status and description/points mapping
    BTM_PENDING = 0
    BTM_NO_STATUS = 1
    BTM_HUMAN = 2
    BTM_KNOWN = 3
    BTM_KNOWN_UNSURE = 4
    BTM_NOT_X_UNSURE = 5
    BTM_KNOWN_UNCERTAIN = 6
    BTM_HOLE = 7
    BTM_NOT_X = 8

    BTM_STATUS = (
        (BTM_PENDING, "Pending"),
        (BTM_NO_STATUS, "NoStatus"),
        (BTM_HUMAN, "Human"),
        (BTM_KNOWN, "Known"),
        (BTM_KNOWN_UNSURE, "KnownUnsure"),
        (BTM_NOT_X_UNSURE, "NotXUnsre"),
        (BTM_KNOWN_UNCERTAIN, "KnownUncertain"),
        (BTM_HOLE, "Hole"),
        (BTM_NOT_X, "NotX"),
    )

    BTM_REWARD_0 = 0
    BTM_REWARD_1 = 1
    BTM_REWARD_2 = 1
    BTM_REWARD_3 = 3
    BTM_REWARD_4 = 4

    BTM_POINTS = {
        BTM_PENDING: 0,
        BTM_NO_STATUS: 0,
        BTM_HUMAN: BTM_REWARD_0,
        BTM_KNOWN: BTM_REWARD_0,
        BTM_KNOWN_UNSURE: BTM_REWARD_1,
        BTM_NOT_X_UNSURE: BTM_REWARD_2,
        BTM_KNOWN_UNCERTAIN: BTM_REWARD_3,
        BTM_HOLE: BTM_REWARD_4,
        BTM_NOT_X: BTM_REWARD_0,
    }

    expected_output = models.CharField(max_length=10, choices=LABEL_CHOICES)
    btm_status = models.IntegerField(default=BTM_PENDING, choices=BTM_STATUS)
    points = models.IntegerField(default=0)

    objects = BeatTheMachineSampleManager()

    @property
    def confidence(self):
        try:
            return self.label_probability[self.label]
        except KeyError:
            return self.label_probability[self.label.capitalize()]

    def updateBTMStatus(self, save=True):
        status = self.calculate_status()

        self.btm_status = status
        self.points = self.BTM_POINTS[status]

        if save:
            self.save()
            if status == self.BTM_HUMAN:
                send_event('EventBTMSendToHuman',
                    sample_id=self.id)

    BTM_STATUS_VERBOSE = {
        BTM_PENDING: "Sample pending.",
        BTM_HUMAN: "Send for verification.",
        BTM_KNOWN: "Known sample.",
    }

    def btm_status_mapping(self):
        try:
            return self.BTM_STATUS_VERBOSE.get(self.btm_status)
        except KeyError:
            log.exception(
                "BTM Sample with errorous state. BTMSample id: %s" % self.id
            )
            return "Error state. It will be verified."

    CONF_HIGH_TRESHOLD = 0.8
    CONF_MEDIUM_TRESHOLD = 0.5
    CONF_HIGH = 1
    CONF_MEDIUM = 2
    CONF_LOW = 3

    @classmethod
    def confidence_level(cls, confidence):
        """
            Conf_high meaning Conf_cl > 80%
            Conf_low meaning Conf_cl > 50% and Conf_cl < 80%
        """
        if confidence > cls.CONF_HIGH_TRESHOLD:
            return cls.CONF_HIGH
        if confidence > cls.CONF_MEDIUM_TRESHOLD:
            return cls.CONF_MEDIUM
        else:
            return cls.CONF_LOW

    def calculate_status(self):
        """ Status calculation using expected output and  classified class
            with its confidence.
        """
        conf_cl = self.confidence
        confidence = self.confidence_level(conf_cl)

        cat_cl = self.label.lower()
        expect = self.expected_output.lower()

        if cat_cl == expect and confidence == self.CONF_HIGH:
            return self.BTM_KNOWN

        elif cat_cl == expect and confidence == self.CONF_MEDIUM:
            return self.BTM_HUMAN

        elif cat_cl != expect and confidence == self.CONF_MEDIUM:
            return self.BTM_HUMAN

        elif cat_cl != expect and confidence == self.CONF_HIGH:
            return self.BTM_HUMAN

        # Should not happened!
        return self.BTM_NO_STATUS

    def recalculate_human(self, cat_h):
        """ Recalculates btm sample status after voting of unsure sample.
        """
        conf_cl = self.confidence
        confidence = self.confidence_level(conf_cl)

        cat_h = cat_h.lower()
        cat_cl = self.label.lower()
        expect = self.expected_output.lower()

        if cat_cl == expect and confidence == self.CONF_MEDIUM:
            if cat_h == expect:
                self.btm_status = self.BTM_KNOWN_UNSURE
            else:
                self.btm_status = self.BTM_NOT_X_UNSURE

        elif cat_cl != expect and confidence == self.CONF_MEDIUM:
            if cat_h == expect:
                self.btm_status = self.BTM_KNOWN_UNCERTAIN
            else:
                self.btm_status = self.BTM_NOT_X_UNSURE

        elif cat_cl != expect and confidence == self.CONF_HIGH:
            if cat_h == expect:
                self.btm_status = self.BTM_HOLE
            else:
                self.btm_status = self.BTM_NOT_X

        self.save()


class TagasaurisJobs(models.Model):
    urlannotator_job = models.OneToOneField(Job)
    sample_gathering_key = models.CharField(max_length=128)
    voting_key = models.CharField(max_length=128, null=True, blank=True)
    voting_btm_key = models.CharField(max_length=128, null=True, blank=True)
    beatthemachine_key = models.CharField(max_length=128, null=True, blank=True)
    sample_gathering_hit = models.CharField(max_length=128, null=True,
        blank=True)
    voting_hit = models.CharField(max_length=128, null=True, blank=True)
    voting_btm_hit = models.CharField(max_length=128, null=True, blank=True)
    beatthemachine_hit = models.CharField(max_length=128, null=True, blank=True)

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
    external_id = models.CharField(max_length=128)
    crowscourcing_type = models.CharField(max_length=20,
        choices=CROWDSOURCING_CHOICES)


class TroiaJob(models.Model):
    job = models.OneToOneField(Job)
    troia_id = models.CharField(max_length=64)
