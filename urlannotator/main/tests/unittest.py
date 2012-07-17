import re
import urllib2
import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import mail
from celery.result import AsyncResult

from social_auth.models import UserSocialAuth

from urlannotator.main.models import Account, Job, Worker, Sample
from urlannotator.main.factories import SampleFactory


class SampleFactoryTest(TestCase):

    def testSimpleSample(self):
        job = Job()
        job.account_id = 1
        job.save()

        worker = Worker()
        worker.save()

        test_url = 'google.com'

        sf = SampleFactory()
        res = sf.new_sample(job, worker, test_url)
        res.get()

        query = Sample.objects.filter(job=job, url=test_url)

        self.assertEqual(query.count(), 1)

        sample = query.get()
        self.assertTrue('Google' in sample.text)

        s = urllib2.urlopen(sample.screenshot)
        self.assertEqual(s.headers.type, 'image/png')


class BaseNotLoggedInTests(TestCase):

    def testLoginNotRestrictedPages(self):
        url_list = [('', 'main/index.html'),
                    (reverse('login'), 'main/login.html'),
                    (reverse('register'), 'main/register.html')]

        for url, template in url_list:
            c = Client()
            resp = c.get(url)

            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, template)
            self.assertFalse(c.session)

            self.assertFalse('projects' in resp.context)
            self.assertFalse('success' in resp.context)
            self.assertFalse('error' in resp.context)

    def testLoginRestrictedPages(self):
        url_list = [('/setttings/', 'main/settings.html'),
                    ('/wizard/', 'main/wizard/project.html')]

        for url, template in url_list:
            c = Client()

            self.assertRaises(c.get(url))

    def testEmailRegister(self):
        c = Client()

        register_url = reverse('register')
        resp = c.post(register_url, {'email': 'testtest.test',
                                     'password1': 'test1',
                                     'password2': 'test'})
        self.assertFormError(resp, 'form', None, 'Passwords do not match.')
        self.assertFormError(resp, 'form', 'email',
                             'Enter a valid e-mail address.')

        resp = c.post(register_url, {'email': 'test@test.test',
                                     'password1': 'test',
                                     'password2': 'test'})
        user = User.objects.get(email='test@test.test')
        # Email backend used for tests
        self.assertTrue(mail.outbox)

        key = re.search(r'/activation/(.+-\d+)', mail.outbox[0].body)
        key = key.group(1)
        self.assertFalse(user.is_active)
        self.assertEqual(user.get_profile().activation_key, key)
        self.assertTrue(user.get_profile().email_registered)

        # Account not activated
        resp = c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test'}, follow=True)

        self.assertIn('error', resp.context)

        bad_key = 'thisisabadkey'
        resp = c.get('/activation/%s' % bad_key)
        self.assertTrue('error' in resp.context)

        bad_key = 'thisisabadkey-20'
        resp = c.get('/activation/%s' % bad_key)
        self.assertTrue('error' in resp.context)

        resp = c.get('/activation/%s' % key, follow=True)
        self.assertTrue('success' in resp.context)
        self.assertEqual(Account.objects.get(id=1).activation_key,
                         'activated')

        resp = c.get('/activation/%s' % key)
        self.assertTrue('error' in resp.context)

        resp = c.post(register_url, {'email': 'test@test.test',
                                     'password1': 'test1',
                                     'password2': 'test'})
        self.assertFormError(resp, 'form', None, 'Passwords do not match.')
        self.assertFormError(resp, 'form', 'email', 'Email is already in use.')

        resp = c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test'})
        # Redirection
        self.assertEqual(resp.status_code, 302)

        resp = c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test',
                                         'remember': 'remember'})
        # Redirection
        self.assertEqual(resp.status_code, 302)

        resp = c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test2'})
        # Redirection
        self.assertEqual(resp.status_code, 302)


class LoggedInTests(TestCase):
    def createProject(self, user):
        p = Job(account=user.get_profile(),
                title='test',
                description='test desc',
                data_source=1,
                status=1)  # Active
        p.save()

    def testDashboard(self):
        c = Client()
        u = User.objects.create_user(username='test2', password='test',
            email='test@test.org')
        c.login(username='test2', password='test')

        resp = c.get(reverse('index'))

        # Empty projects list
        self.assertTrue('projects' in resp.context)
        self.assertTrue(not resp.context['projects'])

        # Populate projects
        self.createProject(u)
        self.createProject(u)

        self.assertTrue(Job.objects.all().count() == 2)
        resp = c.get(reverse('index'))

        self.assertTrue('projects' in resp.context)
        self.assertTrue(len(resp.context['projects']) == 2)

    def testLogIn(self):
        c = Client()
        User.objects.create_user(username='test2', password='test',
            email='test2@test.org')
        resp = c.post(reverse('login'),
            {'email': 'test@test.org', 'password': 'test'}, follow=True)
        self.assertTemplateUsed(resp, 'main/index.html')
        self.assertIn('error', resp.context)

        resp = c.post(reverse('login'),
            {'email': 'testtest.org', 'password': 'test'}, follow=True)
        self.assertTemplateUsed(resp, 'main/index.html')
        self.assertIn('error', resp.context)


class SettingsTests(TestCase):
    def testBasic(self):
        c = Client()
        u = User.objects.create_user(username='test2', password='test',
                                     email='test@test.org')
        c.login(username='test2', password='test')

        resp = c.get(reverse('settings'))
        # User not registered via email
        self.assertFalse('email' in resp.content)
        self.assertFalse('password' in resp.content)

        resp = c.post(reverse('settings'), {'full_name': 'test',
            'submit': 'general'})
        self.assertTrue('success' in resp.context)
        self.assertEqual(resp.context['success'],
                         'Full name has been successfully changed.')

        u.get_profile().email_registered = True
        u.get_profile().save()

        resp = c.post(reverse('settings'), {'full_name': 'test',
            'email': 'test@test.org', 'submit': 'general'})
        self.assertTrue('success' in resp.context)
        self.assertEqual(resp.context['success'],
                         'Full name has been successfully changed.')

        # Password change
        resp = c.post(reverse('settings'), {'old_password': 'test2',
            'submit': 'password'})
        self.assertFormError(resp, 'password_form', 'old_password',
            'Your old password was entered incorrectly. '
            'Please enter it again.')

        resp = c.post(reverse('settings'), {'old_password': 'test',
            'submit': 'password', 'new_password1': 'test2',
            'new_password2': 'test2'},
            follow=True)
        self.assertIn('success', resp.context)

        # Alerts
        resp = c.post(reverse('settings'), {'alerts': None,
            'submit': 'alerts'})
        self.assertFormError(resp, 'alerts_form', 'alerts', [])

        resp = c.post(reverse('settings'), {'alerts': 'alerts',
            'submit': 'alerts'},
            follow=True)
        self.assertIn('success', resp.context)

        resp = c.post(reverse('settings'), {'submit': 'wrongsubmit'})
        self.assertTemplateUsed(resp, 'main/settings.html')
        self.assertNotIn('error', resp.context)
        self.assertNotIn('success', resp.context)

    def testAssociation(self):
        c = Client()
        u = User.objects.create_user(username='test2', password='test',
                                     email='test@test.org')
        c.login(username='test2', password='test')

        resp = c.get(reverse('settings'))
        self.assertNotIn('facebook', resp.context)
        self.assertNotIn('google', resp.context)
        self.assertNotIn('twitter', resp.context)
        self.assertNotIn('odesk', resp.context)

        u.get_profile().odesk_uid = 1
        u.get_profile().full_name = "Testing Test"
        u.get_profile().save()

        # Odesk assoc
        resp = c.get(reverse('settings'))
        self.assertIn('odesk', resp.context)

        # Facebook assoc
        usa = UserSocialAuth(user=u, provider='facebook', uid='Tester')
        usa.save()

        resp = c.get(reverse('settings'))
        self.assertIn('facebook', resp.context)

        # Google assoc
        usa = UserSocialAuth(user=u, provider='google-oauth2', uid='Tester')
        usa.save()

        resp = c.get(reverse('settings'))
        self.assertIn('google', resp.context)

        # Twitter assoc
        usa = UserSocialAuth(user=u, provider='twitter', uid='Tester')
        usa.save()

        resp = c.get(reverse('settings'))
        self.assertIn('twitter', resp.context)


class ProjectTests(TestCase):
    def testBasic(self):
        c = Client()
        u = User.objects.create_user(username='test2', password='test',
                                     email='test@test.org')
        c.login(username='test2', password='test')

        # No odesk association - display alert
        resp = c.get(reverse('project_wizard'))

        self.assertTrue(resp.status_code in [200, 302])
        self.assertTrue('wizard_alert' in resp.context)

        # Invalid option - odesk chosen, account not connected
        odesk_sources = ['0', '2']
        error_text = 'You have to be connected to Odesk to use this option.'
        for source in odesk_sources:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': source,
                    'project_type': '0',
                    'no_of_urls': '0',
                    'hourly_rate': '1.0',
                    'budget': '1.0',
                    'same_domain': '0',
                    'submit': 'draft'}

            resp = c.post(reverse('project_wizard'), data)
            self.assertFormError(resp, 'attributes_form', None, error_text)

        prof = u.get_profile()
        prof.odesk_uid = 'test'
        prof.save()

        # Odesk is associated
        resp = c.get(reverse('project_wizard'))

        self.assertTrue(resp.status_code in [200, 302])
        self.assertFalse('wizard_alert' in resp.context)

        # Check project creation

        # Odesk free project type
        # Missing data source values, get defaults
        for submit in ['draft', 'active']:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': '0',
                    'same_domain': '0',
                    'submit': submit}

            resp = c.post(reverse('project_wizard'), data, follow=True)
            self.assertTemplateUsed(resp, 'main/project/overview.html')

        # Selected project type, missing values, get defaults
        for submit in ['draft', 'active']:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': '0',
                    'project_type': '0',
                    'same_domain': '0',
                    'submit': submit}

            resp = c.post(reverse('project_wizard'), data, follow=True)
            self.assertTemplateUsed(resp, 'main/project/overview.html')

        # Missing one of values from project type
        for submit in ['draft', 'active']:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': '0',
                    'project_type': '0',
                    'no_of_urls': '0',
                    'same_domain': '0',
                    'submit': submit}

            resp = c.post(reverse('project_wizard'), data, follow=True)
            self.assertTemplateUsed(resp, 'main/project/overview.html')

        for submit in ['draft', 'active']:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': '0',
                    'project_type': '1',
                    'same_domain': '0',
                    'submit': submit}

            resp = c.post(reverse('project_wizard'), data, follow=True)
            self.assertTemplateUsed(resp, 'main/project/overview.html')

        # Full values provided
        for source in ['0', '1', '2']:
            for submit in ['draft', 'active']:
                data = {'topic': 'Test',
                        'topic_desc': 'Test desc',
                        'data_source': source,
                        'project_type': '0',
                        'no_of_urls': '0',
                        'hourly_rate': '1.0',
                        'budget': '1.0',
                        'same_domain': '0',
                        'submit': submit}

                resp = c.post(reverse('project_wizard'), data, follow=True)
                self.assertTemplateUsed(resp, 'main/project/overview.html')

        # Check project topic and description
        data = {'topic_desc': 'Test desc',
                'data_source': '1',
                'project_type': '0',
                'no_of_urls': '0',
                'hourly_rate': '1.0',
                'budget': '1.0',
                'same_domain': '0',
                'submit': 'draft'}

        resp = c.post(reverse('project_wizard'), data)
        self.assertFormError(resp, 'topic_form', 'topic',
                             'Please input project topic.')

        data = {'topic': 'Test',
                'data_source': '1',
                'project_type': '0',
                'no_of_urls': '0',
                'hourly_rate': '1.0',
                'budget': '1.0',
                'same_domain': '0',
                'submit': 'draft'}

        resp = c.post(reverse('project_wizard'), data)
        self.assertFormError(resp, 'topic_form', 'topic_desc',
                             'Please input project topic description.')

class ApiTests(TestCase):
    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='testing',
            password='test')
        self.user.save()

    def testJobs(self):
        c = Client()
        resp = c.get('/api/v1/job/?format=json', follow=True)

        array = json.loads(resp.content)
        self.assertIn('meta', array)

        Job(account=self.user.get_profile()).save()
        resp = c.get('%s%s?format=json' % (self.api_url, 'job/1/'),
            follow=True)

        array = json.loads(resp.content)
        self.assertIn('status', array)

        resp = c.get('%s%s?format=json' % (self.api_url, 'job/1/classify/'),
            follow=True)

        array = json.loads(resp.content)
        self.assertIn('error', array)

        resp = c.get('%s%s?format=json&url=example.com'
            % (self.api_url, 'job/2/classify/'), follow=True)

        array = json.loads(resp.content)
        self.assertIn('error', array)

        resp = c.get('%s%stest/?format=json' % (self.api_url, 'job/1/classify/'),
            follow=True)

        array = json.loads(resp.content)
        self.assertIn('error', array)

        resp = c.get('%s%stest/?format=json' % (self.api_url, 'job/2/classify/'),
            follow=True)

        array = json.loads(resp.content)
        self.assertIn('error', array)
