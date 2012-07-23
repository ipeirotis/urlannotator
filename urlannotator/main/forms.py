from django import forms
from django.contrib.auth.models import User

from urlannotator.main.models import JOB_BASIC_DATA_SOURCE_CHOICES,\
    JOB_DATA_SOURCE_CHOICES, JOB_TYPE_CHOICES, Job


class NewUserForm(forms.Form):
    """ Form to create new users.
    """
    email = forms.EmailField(label="E-mail")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput,
        label="Confirm password")

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
        else:
            raise forms.ValidationError('Enter password twice.')
        return cleaned


class GeneralUserForm(forms.Form):
    """ Form displayed in settings for users registered with social accounts.
    """
    full_name = forms.CharField(label="Full name", required=False)


class GeneralEmailUserForm(GeneralUserForm):
    """ Form displayed in settings for users registered with an email address.
    """
    email = forms.EmailField(widget=forms.TextInput(attrs={'readonly': True}))


class AlertsSetupForm(forms.Form):
    """ Form allowing setting up user alerts.
    """
    alerts = forms.BooleanField(required=False)


class UserLoginForm(forms.Form):
    """ Form allowing e-mail registered users to log in.
    """
    email = forms.EmailField(label="E-mail")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")


class WizardTopicForm(forms.Form):
    """ Form representing project wizard's topic part.
    """
    topic = forms.CharField(required=False, label="Topic",
            help_text="E.g Identify pages that contain hate speech on the web")
    topic_desc = forms.CharField(required=False, widget=forms.Textarea,
        label="Topic description",
        help_text='E.g Find sites which advocate hostility or aggression</br>'
        'toward individuals or groups on the basis of race,</br>'
        'religion, gender, nationality, ethnic origni, or other</br>'
        'involuntary characteristic.')

    def clean_topic(self):
        topic = self.cleaned_data['topic']
        if not topic:
            raise forms.ValidationError('Please input project topic.')
        return topic

    def clean_topic_desc(self):
        topic_desc = self.cleaned_data['topic_desc']
        if not topic_desc:
            raise forms.ValidationError(
                'Please input project topic description.')
        return topic_desc


class WizardAttributesForm(forms.Form):
    """ Form representing project wizard's attributes part.
    """
    data_source = forms.ChoiceField(JOB_BASIC_DATA_SOURCE_CHOICES,
        label="Data source",
        help_text="You have 800 free URL quota provided by Odesk")
    project_type = forms.ChoiceField(JOB_TYPE_CHOICES, required=False,
        label="Project type")
    no_of_urls = forms.IntegerField(required=False,
        label="No. of URLs to collect")
    hourly_rate = forms.DecimalField(required=False, decimal_places=2,
        max_digits=10, label="Hourly rate (US$)")
    budget = forms.DecimalField(required=False, decimal_places=2,
        max_digits=10, label="Declared budget")
    odesk_connect = False

    def __init__(self, odeskConnected=False, *args, **kwargs):
        super(WizardAttributesForm, self).__init__(*args, **kwargs)
        # If user is connected to odesk, add new choices
        if odeskConnected:
            self.fields['data_source'].choices = JOB_DATA_SOURCE_CHOICES
            self.odesk_connect = True

    def _clean_value(self, dict, key, val):
        var = dict.get(key, val)
        if not var:
            var = val
        dict[key] = var

    def clean(self):
        cleaned_data = super(WizardAttributesForm, self).clean()

        self._clean_value(cleaned_data, 'data_source', '0')

        if (Job.is_odesk_required_for_source(cleaned_data['data_source']) and
            not self.odesk_connect):
            raise forms.ValidationError(
              'You have to be connected to Odesk to use this option.')

        if cleaned_data['data_source'] == '1':
            cleaned_data['hourly_rate'] = 0
            cleaned_data['budget'] = 0
        else:
            self._clean_value(cleaned_data, 'project_type', '0')

            if cleaned_data['project_type'] == '0':
                cleaned_data['budget'] = 0
                self._clean_value(cleaned_data, 'no_of_urls', '0')
                self._clean_value(cleaned_data, 'hourly_rate', '0')
            else:
                cleaned_data['no_of_urls'] = 0
                cleaned_data['hourly_rate'] = 0
                self._clean_value(cleaned_data, 'budget', '0')
        return cleaned_data


class WizardAdditionalForm(forms.Form):
    """ Form representing project wizard's additional fields
    """
    same_domain = forms.IntegerField(
        label="No. of allowed multiple URLs from the same domain")
    file_gold_urls = forms.FileField(required=False,
        label="Upload gold, (preclassified) urls", help_text="(i)")
    file_classify_urls = forms.FileField(required=False,
        label="Upload additional non classified URLs", help_text="(i)")
