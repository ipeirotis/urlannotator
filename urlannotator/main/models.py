from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save


# Create your models here.
class Account(models.Model):
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

JOB_BASIC_DATA_SOURCE_CHOICES = ((1, 'Own workforce'),)
JOB_DATA_SOURCE_CHOICES = JOB_BASIC_DATA_SOURCE_CHOICES + \
                          ((0, 'Odesk free'), (2, 'Odesk paid'))
JOB_TYPE_CHOICES = ((0, 'Fixed no. of URLs to collect'), (1, 'Fixed price'))
JOB_STATUS_CHOICES = ((0, 'Draft'), (1, 'Active'), (2, 'Completed'),
                      (3, 'Stopped'))


class Job(models.Model):
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
    # project_status = models.IntegerField(default=0, choices=JOB_STATUS_CHOICES)
    hourly_rate = models.DecimalField(default=0, decimal_places=2,
                                      max_digits=10)
    budget = models.DecimalField(default=0, decimal_places=2, max_digits=10)

    def get_status(self):
        return JOB_STATUS_CHOICES[self.status][1]

    def is_draft(self):
        return self.status == 0

    @staticmethod
    def is_odesk_required_for_source(source):
        return int(source) != 1


class Worker(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    estimated_quality = models.DecimalField(default=0, decimal_places=5,
                                            max_digits=7)
