import re
import urllib2
import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import mail

from social_auth.models import UserSocialAuth

from urlannotator.main.models import (Account, Job, Worker, Sample, GoldSample,
    ClassifiedSample)
from urlannotator.main.factories import SampleFactory


class SampleFactoryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='1')
        self.job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'example.com', 'label': 'Yes'}])
        )

    def testSimpleSample(self):
        worker = Worker()
        worker.save()

        test_url = 'google.com'

        sf = SampleFactory()
        res = sf.new_sample(self.job.id, worker.id, test_url)
        res.get()

        query = Sample.objects.filter(job=self.job, url=test_url)

        self.assertEqual(query.count(), 1)

        sample = query.get()
        self.assertTrue('google' in sample.text)

        print 'ss', sample.screenshot
        s = urllib2.urlopen(sample.screenshot)
        self.assertEqual(s.headers.type, 'image/png')


class JobFactoryTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='test2', password='1')

    def testJobFactory(self):
        Job.objects.create_draft(account=self.u.get_profile())

        # Nothing new added
        self.assertEqual(Sample.objects.all().count(), 0)

        gold_samples = [{'url': 'google.com', 'label': 'Yes'}]
        Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=json.dumps(gold_samples)
        )

        # New sample created
        self.assertEqual(Sample.objects.all().count(), 1)
        self.assertEqual(GoldSample.objects.all().exclude(label='').count(), 1)


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
        Job.objects.create_active(
            account=user.get_profile(),
            title='test',
            description='test desc',
            data_source=1,
            status=1
        )

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

        Worker(external_id=1).save()
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
    def setUp(self):
        self.c = Client()
        self.u = User.objects.create_user(username='test2', password='test',
                                     email='test@test.org')
        self.c.login(username='test2', password='test')
        Sample.objects.all().delete()
        GoldSample.objects.all().delete()
        ClassifiedSample.objects.all().delete()

    def testBasic(self):
        # No odesk association - display alert
        resp = self.c.get(reverse('project_wizard'), follow=True)

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

            resp = self.c.post(reverse('project_wizard'), data, follow=True)
            self.assertFormError(resp, 'attributes_form', None, error_text)

        prof = self.u.get_profile()
        prof.odesk_uid = 'test'
        prof.save()

        # Odesk is associated
        resp = self.c.get(reverse('project_wizard'), follow=True)

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

            resp = self.c.post(reverse('project_wizard'), data, follow=True)
            self.assertTemplateUsed(resp, 'main/project/overview.html')

        # Selected project type, missing values, get defaults
        for submit in ['draft', 'active']:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': '0',
                    'project_type': '0',
                    'same_domain': '0',
                    'submit': submit}

            resp = self.c.post(reverse('project_wizard'), data, follow=True)
            self.assertTemplateUsed(resp, 'main/project/overview.html')

        # Missing one of values from project type
        for submit in ['draft', 'active']:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': '0',
                    'project_type': '0',
                    'same_domain': '0',
                    'submit': submit}

            resp = self.c.post(reverse('project_wizard'), data, follow=True)
            self.assertTemplateUsed(resp, 'main/project/overview.html')

        for submit in ['draft', 'active']:
            data = {'topic': 'Test',
                    'topic_desc': 'Test desc',
                    'data_source': '0',
                    'project_type': '1',
                    'same_domain': '0',
                    'submit': submit}

            resp = self.c.post(reverse('project_wizard'), data, follow=True)
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

                resp = self.c.post(reverse('project_wizard'), data, follow=True)
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

        resp = self.c.post(reverse('project_wizard'), data, follow=True)
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

        resp = self.c.post(reverse('project_wizard'), data, follow=True)
        self.assertFormError(resp, 'topic_form', 'topic_desc',
                             'Please input project topic description.')

        data = {'topic': 'Test',
                'topic_desc': 'a',
                'data_source': '1',
                'project_type': '0',
                'same_domain': '0',
                'submit': 'active'}

        resp = self.c.post(reverse('project_wizard'), data, follow=True)
        self.assertEqual(resp.status_code, 200)

    def testOverview(self):
        Job.objects.create_active(
            title='test',
            description='test',
            account=self.u.get_profile()
        )

        project_urls = ['view', 'workers_view', 'data_view',
            'btm_view', 'classifier_view']

        # Correct display
        for view in project_urls:
            resp = self.c.get(reverse('project_%s' % view, args=[1]),
                follow=True)
            self.assertEqual(resp.status_code, 200)

        # Wrong job id - missing job
        for view in project_urls:
            resp = self.c.get(reverse('project_%s' % view, args=[0]),
                follow=True)
            self.assertIn('error', resp.context)

        resp = self.c.get(reverse('project_worker_view', args=[1, 1]),
            follow=True)
        self.assertEqual(resp.status_code, 200)

        resp = self.c.get(reverse('project_worker_view', args=[0, 1]),
            follow=True)
        self.assertEqual(resp.status_code, 200)

    def testClassifierView(self):
        job = Job.objects.create_active(
            title='test',
            description='test',
            account=self.u.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        self.assertTrue(GoldSample.objects.filter(label='').count() == 0)

        testUrl = 'google.com'
        self.c.post(reverse('project_classifier_view', args=[1]),
            {'test-urls': testUrl}, follow=True)

        # Gold sample + classification request
        self.assertEqual(ClassifiedSample.objects.all().count(), 2)
        # Gold sample + new sample (new sample shares url with gold sample)
        self.assertEqual(Sample.objects.filter(url=testUrl, job=job).count(),
            1)

        testUrl = 'example.com'
        self.c.post(reverse('project_classifier_view', args=[1]),
            {'test-urls': testUrl}, follow=True)

        # classification request + old data
        self.assertEqual(ClassifiedSample.objects.all().count(), 3)
        # old data + new sample
        self.assertEqual(Sample.objects.filter(job=job).count(),
            2)

        # Create a new job and check uniqueness
        job = Job.objects.create_active(
            title='test',
            description='test',
            account=self.u.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        testUrl = 'example.com'
        self.c.post(reverse('project_classifier_view', args=[job.id]),
            {'test-urls': testUrl}, follow=True)

        # classification request + old data
        self.assertEqual(ClassifiedSample.objects.all().count(), 5)
        # old data + new sample
        self.assertEqual(Sample.objects.filter(job=job).count(),
            2)


class DocsTest(TestCase):
    def testDocs(self):
        c = Client()

        c.get(reverse('readme_view'), follow=True)
        self.assertTrue(True)


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

        Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

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

        resp = c.get('%s%s?format=json&request=test'
            % (self.api_url, 'job/1/classify/status/'), follow=True)

        array = json.loads(resp.content)
        self.assertIn('error', array)

        resp = c.get('%s%s?format=json&url=google.com'
            % (self.api_url, 'job/1/classify/'), follow=True)

        array = json.loads(resp.content)
        print array
        request_id = array['request_id']

        resp = c.get('%s%s?format=json&url=google.com&request=%s'
            % (self.api_url, 'job/1/classify/status/', request_id),
            follow=True)

        array = json.loads(resp.content)
        self.assertIn('status', array)

        resp = c.get('%s%s?format=json&request=test'
            % (self.api_url, 'job/2/classify/'), follow=True)

        array = json.loads(resp.content)
        self.assertIn('error', array)
