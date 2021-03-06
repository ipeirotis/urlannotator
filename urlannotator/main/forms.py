from django import forms
from django.contrib.auth.models import User

from urlannotator.main.models import JOB_BASIC_DATA_SOURCE_CHOICES


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
        required=True,
        label="Data source")
    no_of_urls = forms.IntegerField(required=True,
        label="No. of URLs to collect", min_value=1)


class WizardAdditionalForm(forms.Form):
    """ Form representing project wizard's additional fields
    """
    additional_gold_info = ("Entries in the file should be in format "
        "\"url\",Yes/No per line.<br/>E.g. \"http://google.com\",Yes.")
    additional_classify_info = ("Entries should be in format \"url\" per line."
        "<br/>E.g. \"http://google.com\".")
    filler_samples_info = ("Includes gold samples labeled as \"No\" in number "
        "equal to number of urls to gather.")
    icon = "<i title='%s' class='icon-info-sign pop'></i>"
    gold_help_text = icon % additional_gold_info
    classify_help_text = icon % additional_classify_info
    filler_samples_help_text = filler_samples_info
    add_filler_samples = forms.BooleanField(required=False, initial=False,
        label='Additional gold samples', help_text=filler_samples_help_text)
    same_domain = forms.IntegerField(
        label="No. of allowed multiple URLs from the same domain",
        min_value=1)
    file_gold_urls = forms.FileField(required=False,
        label="Upload gold, (preclassified) urls", help_text=gold_help_text)
    gold_urls_positive = forms.CharField(required=False, widget=forms.Textarea,
        label="Positive URLs (that match your search)",
        help_text='Here you can add your URLs. End each one with enter')
    gold_urls_negative = forms.CharField(required=False, widget=forms.Textarea,
        label="Negative URLs (that don't match your search)",
        help_text='Here you can add your URLs. End each one with enter')
    file_classify_urls = forms.FileField(required=False,
        label="Upload additional non classified URLs", help_text=classify_help_text)


class BTMForm(forms.Form):
    topic = forms.CharField(required=True, label="Topic",
            help_text="E.g Identify pages that contain hate speech on the web.")
    topic_desc = forms.CharField(required=True, widget=forms.Textarea,
        label="Topic description",
        help_text='E.g Find sites which advocate hostility or aggression</br>'
        'toward individuals or groups on the basis of race,</br>'
        'religion, gender, nationality, ethnic origni, or other</br>'
        'involuntary characteristic.')
    no_of_urls = forms.IntegerField(min_value=1, label='Number of urls')
    points_to_cash = forms.IntegerField(min_value=1,
        label='Points to dollars conversion rate')
