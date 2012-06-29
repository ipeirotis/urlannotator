from django import forms
from django.contrib.auth.models import User

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
