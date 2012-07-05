from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# Create your models here.
class UserProfile(models.Model):
    user = models.ForeignKey(User)
    activation_key = models.CharField(max_length=100)
    email_registered = models.BooleanField(default=False)
    full_name = models.CharField(default='', max_length=100)
    alerts = models.BooleanField(default=False)
  
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)

class UserOdeskAssociation(models.Model):
    user = models.ForeignKey(User, related_name='odesk')
    uid = models.CharField(max_length=100)
    token = models.CharField(max_length=100)
    full_name = models.CharField(max_length=100)

PROJECT_BASIC_DATA_SOURCE_CHOICES = ((1, 'Own workforce'),)
PROJECT_DATA_SOURCE_CHOICES = tuple(list(PROJECT_BASIC_DATA_SOURCE_CHOICES) + [(0, 'Odesk free'), (2, 'Odesk paid')])
PROJECT_TYPE_CHOICES = ((0, 'Fixed no. of URLs to collect'), (1, 'Fixed price'))
PROJECT_STATUS_CHOICES = ((0, 'Draft'), (1, 'Active'), (2, 'Completed'), (3, 'Stopped'))

class Project(models.Model):
    author = models.ForeignKey(User, related_name='project')
    topic = models.CharField(max_length=100)
    topic_desc = models.TextField()
    data_source = models.IntegerField(default=1, choices=PROJECT_DATA_SOURCE_CHOICES)
    project_type = models.IntegerField(default=0, choices=PROJECT_TYPE_CHOICES)
    no_of_urls = models.PositiveIntegerField(default=0)
    same_domain_allowed = models.PositiveIntegerField(default=0)
    project_status = models.IntegerField(default=0, choices=PROJECT_STATUS_CHOICES)
    hourly_rate = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    budget = models.DecimalField(default=0, decimal_places=2, max_digits=10)

    def get_status(self):
        return PROJECT_STATUS_CHOICES[self.project_status][1]

    def is_draft(self):
        return self.project_status == 0

class ProjectInfo(models.Model):
    project = models.ForeignKey(Project)
  
def create_project_info(sender, instance, created, **kwargs):
    if created:
        ProjectInfo.objects.create(project=instance)

post_save.connect(create_project_info, sender=Project)