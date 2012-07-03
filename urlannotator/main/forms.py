from django import forms
from django.contrib.auth.models import User

from urlannotator.main.models import *

class NewUserForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    
    def clean_email(self):
        cleaned = self.cleaned_data['email']
        if User.objects.filter(username=cleaned):
            raise forms.ValidationError('Email is already in use.')
        return cleaned
    
    def clean(self):
        cleaned = super(NewUserForm, self).clean()
        if 'password1' in cleaned and 'password2' in cleaned:
            if cleaned['password1'] != cleaned['password2']:
              raise forms.ValidationError('Passwords do not match.')
        return cleaned

class GeneralUserForm(forms.Form):
    full_name = forms.CharField(label="Full name",required=False)

class GeneralEmailUserForm(GeneralUserForm):
    email = forms.EmailField(widget=forms.TextInput(attrs={'readonly':True}))

class AlertsSetupForm(forms.Form):
    alerts = forms.BooleanField(required=False)
  
class UserLoginForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

class WizardTopicForm(forms.Form):
    topic = forms.CharField(label="Topic", help_text="E.g Identify pages that contain hate speech on the web")
    topic_desc = forms.CharField(widget=forms.Textarea,label="Topic description", help_text='''E.g Find sites which advocate hostility or aggression</br>
                                                                                               toward individuals or groups on the basis of race,</br>
                                                                                               religion, gender, nationality, ethnic origni, or other</br>
                                                                                               involuntary characteristic.''')

class WizardAttributesForm(forms.Form):
    data_source = forms.ChoiceField(PROJECT_DATA_SOURCE_CHOICES, label="Data source", help_text="You have 800 free URL quota provided by Odesk")
    project_type = forms.ChoiceField(PROJECT_TYPE_CHOICES, label="Project type")
    no_of_urls = forms.IntegerField(label="No. of URLs to collect")
    hourly_rate = forms.DecimalField(decimal_places=2,max_digits=10,label="Hourly rate (US$)")
    budget = forms.DecimalField(decimal_places=2,max_digits=10,label="Declared budget")

class WizardAdditionalForm(forms.Form):
    same_domain = forms.IntegerField(required=False,label="No. of allowed multiple URLs from the same domain")
    file_gold_urls = forms.FileField(required=False,label="Upload gold, (preclassified) urls", help_text="(i)")
    file_norm_urls = forms.FileField(required=False,label="Upload additional non classified URLs", help_text="(i)")
