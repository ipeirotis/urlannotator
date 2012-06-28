from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# Create your models here.
class UserProfile(models.Model):
  user = models.ForeignKey(User)
  activation_key = models.CharField(max_length=100)
  email_registered = models.BooleanField(default=False)
  full_name = models.CharField(default='',max_length=100)
  alerts = models.BooleanField(default=False)
  
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
