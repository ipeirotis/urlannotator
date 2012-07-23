from tastypie.models import create_api_key

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from tenclouds.django.jsonfield.fields import JSONField

LABEL_CHOICES = (('Yes', 'Yes'), ('No', 'No'), ('Broken', 'Broken'))


class Account(models.Model):
    """
        Model representing additional user data. Used as user profile.
    """
    user = models.ForeignKey(User)
    activation_key = models.CharField(default='', max_length=100)
    email_registered = models.BooleanField(default=False)
    odesk_key = models.CharField(default='', max_length=100)
    odesk_uid = models.CharField(default='', max_length=100)
    full_name = models.CharField(default='', max_length=100)
    alerts = models.BooleanField(default=False)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
post_save.connect(create_api_key, sender=User)

JOB_BASIC_DATA_SOURCE_CHOICES = ((1, 'Own workforce'),)
JOB_DATA_SOURCE_CHOICES = JOB_BASIC_DATA_SOURCE_CHOICES + \
                          ((0, 'Odesk free'), (2, 'Odesk paid'))
JOB_TYPE_CHOICES = ((0, 'Fixed no. of URLs to collect'), (1, 'Fixed price'))

# Job status breakdown:
# Draft - template of a job, not active yet, can be started.
# Active - up and running job.
# Completed - job has reached it's goal. Possible BTM still running.
# Stopped - job has been stopped by it's owner.
# Created - job has been just created by user, awaiting initialization of
#           elements. An active job must've gone through this step.
#           Drafts DO NOT get this status.
JOB_STATUS_CHOICES = ((0, 'Draft'), (1, 'Active'), (2, 'Completed'),
                      (3, 'Stopped'), (4, 'Created'))


class Job(models.Model):
    """
        Model representing actual project that is start by user, and consists
        of gathering, verifying and classifying samples.
    """
    account = models.ForeignKey(Account, related_name='project')
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.IntegerField(default=0, choices=JOB_STATUS_CHOICES)
    progress = models.IntegerField(default=0)
    no_of_urls = models.PositiveIntegerField(default=0)
    data_source = models.IntegerField(default=1,
        choices=JOB_DATA_SOURCE_CHOICES)
    project_type = models.IntegerField(default=0, choices=JOB_TYPE_CHOICES)
    same_domain_allowed = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(default=0, decimal_places=2,
        max_digits=10)
    gold_samples = JSONField()
    classify_urls = JSONField()
    budget = models.DecimalField(default=0, decimal_places=2, max_digits=10)

    def get_status(self):
        return JOB_STATUS_CHOICES[self.status][1]

    def is_draft(self):
        return self.status == 0

    @staticmethod
    def is_odesk_required_for_source(source):
        return int(source) != 1


class Worker(models.Model):
    """
        Represents the worker who has completed a HIT.
    """
    external_id = models.CharField(max_length=100)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    estimated_quality = models.DecimalField(default=0, decimal_places=5,
        max_digits=7)


class Sample(models.Model):
    """
        A sample used to classify and verify.
    """
    job = models.ForeignKey(Job)
    url = models.URLField()
    text = models.TextField()
    screenshot = models.URLField()
    label = models.CharField(max_length=10, choices=LABEL_CHOICES, blank=False)
    source = models.CharField(max_length=100, blank=False)
    added_by = models.ForeignKey(Worker)
    added_on = models.DateField(auto_now_add=True)


class TemporarySample(models.Model):
    """
        Temporary sample used inbetween creating the real sample by processes
        responsible for each part.
    """
    text = models.TextField()
    screenshot = models.URLField()


class GoldSample(models.Model):
    """
        Sample uploaded by project owner. It is already classified and is used
        to train classifier.
    """
    sample = models.ForeignKey(Sample)
    label = models.CharField(max_length=10, choices=LABEL_CHOICES)


class ClassifiedSample(models.Model):
    """
        A sample classification request was made for. The sample field is set
        when corresponding sample is created.
    """
    sample = models.ForeignKey(Sample, blank=True, null=True)
    url = models.URLField()
    job = models.ForeignKey(Job)
