import re
import urllib2
import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core import mail
from tastypie.exceptions import ImmediateHttpResponse

from social_auth.models import UserSocialAuth

from urlannotator.main.models import Account, Job, Worker, Sample, GoldSample
from urlannotator.classification.models import ClassifiedSample
from urlannotator.main.factories import SampleFactory
from urlannotator.main.api.resources import (sanitize_positive_int,
    paginate_list, AlertResource, ClassifiedSampleResource)
from urlannotator.logging.models import LogEntry


class SampleFactoryTest(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

    def testSimpleSample(self):
        test_url = 'http://google.com'

        with self.settings(TOOLS_TESTING=False):
            sf = SampleFactory()
            res = sf.new_sample(
                job_id=self.job.id,
                url=test_url,
                source_type=''
            )
        res.get()

        query = Sample.objects.filter(job=self.job, url=test_url)

        self.assertEqual(query.count(), 1)

        sample = query.get()
        self.assertTrue('google' in sample.text)

        s = urllib2.urlopen(sample.screenshot)
        self.assertEqual(s.headers.type, 'image/jpeg')

        # Check for broken urls - sample shouldn't be created
        with self.settings(TOOLS_TESTING=False):
            sf = SampleFactory()
            res = sf.new_sample(
                job_id=self.job.id,
                url=test_url,
                source_type=''
            )
        res.get()

        query = Sample.objects.filter(job=self.job, url=test_url)

        self.assertEqual(query.count(), 1)


class JobFactoryTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

    def testJobFactory(self):
        Job.objects.create_draft(account=self.u.get_profile())

        # Nothing new added.
        self.assertEqual(Sample.objects.all().count(), 0)

        gold_samples = [{'url': 'google.com', 'label': 'Yes'}]
        Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=json.dumps(gold_samples)
        )

        # New sample created
        self.assertEqual(Sample.objects.all().count(), 1)
        # New Gold Sample
        self.assertEqual(GoldSample.objects.all().exclude(label='').count(), 1)


class BaseNotLoggedInTests(TestCase):
    def setUp(self):
        self.c = Client()

    def testLoginNotRestrictedPages(self):
        url_list = [('', 'main/index.html'),
                    (reverse('login'), 'main/login.html'),
                    (reverse('register'), 'main/register.html')]

        for url, template in url_list:
            resp = self.c.get(url)

            self.assertEqual(resp.status_code, 200)
            self.assertTemplateUsed(resp, template)
            self.assertFalse(self.c.session)

            self.assertFalse('projects' in resp.context)
            self.assertFalse('success' in resp.context)
            self.assertFalse('error' in resp.context)

    def testLoginRestrictedPages(self):
        url_list = [('/setttings/', 'main/settings.html'),
                    ('/wizard/', 'main/wizard/project.html')]

        for url, template in url_list:
            self.assertRaises(self.c.get(url))

    def testEmailRegister(self):
        register_url = reverse('register')
        resp = self.c.post(register_url, {'email': 'testtest.test',
                                     'password1': 'test1',
                                     'password2': 'test'})
        self.assertFormError(resp, 'form', None, 'Passwords do not match.')
        self.assertFormError(resp, 'form', 'email',
                             'Enter a valid e-mail address.')

        resp = self.c.post(register_url, {'email': 'test@test.test',
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
        resp = self.c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test'}, follow=True)

        self.assertIn('error', resp.context)

        bad_key = 'thisisabadkey'
        resp = self.c.get('/activation/%s' % bad_key)
        self.assertTrue('error' in resp.context)

        bad_key = 'thisisabadkey-20'
        resp = self.c.get('/activation/%s' % bad_key)
        self.assertTrue('error' in resp.context)

        resp = self.c.get('/activation/%s' % key, follow=True)
        self.assertTrue('success' in resp.context)
        self.assertEqual(Account.objects.get(id=1).activation_key,
                         'activated')

        resp = self.c.get('/activation/%s' % key)
        self.assertTrue('error' in resp.context)

        resp = self.c.post(register_url, {'email': 'test@test.test',
                                     'password1': 'test1',
                                     'password2': 'test'})
        self.assertFormError(resp, 'form', None, 'Passwords do not match.')
        self.assertFormError(resp, 'form', 'email', 'Email is already in use.')

        resp = self.c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test'})
        # Redirection
        self.assertEqual(resp.status_code, 302)

        resp = self.c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test',
                                         'remember': 'remember'})
        # Redirection
        self.assertEqual(resp.status_code, 302)

        resp = self.c.post(reverse('login'), {'email': 'test@test.test',
                                         'password': 'test2'})
        # Redirection
        self.assertEqual(resp.status_code, 302)


class LoggedInTests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.c = Client()
        self.c.login(username='testing', password='test')

    def createProject(self, user):
        Job.objects.create_active(
            account=user.get_profile(),
            title='test',
            description='test desc',
            data_source=1,
            status=1
        )

    def testDashboard(self):
        resp = self.c.get(reverse('index'))

        # Populate projects
        self.createProject(self.u)
        self.createProject(self.u)

        self.assertEqual(Job.objects.all().count(), 2)
        resp = self.c.get(reverse('index'))

        self.assertTrue('projects' in resp.context)
        self.assertEqual(len(resp.context['projects']), 2)

    def testLogIn(self):
        resp = self.c.post(reverse('login'),
            {'email': 'test@test.org', 'password': 'test'}, follow=True)
        self.assertTemplateUsed(resp, 'main/index.html')
        self.assertIn('error', resp.context)

        resp = self.c.post(reverse('login'),
            {'email': 'testtest.org', 'password': 'test'}, follow=True)
        self.assertTemplateUsed(resp, 'main/index.html')
        self.assertIn('error', resp.context)


class SettingsTests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.c = Client()
        self.c.login(username='testing', password='test')

    def testBasic(self):
        resp = self.c.get(reverse('settings'))
        # User not registered via email
        self.assertFalse('email' in resp.content)
        self.assertFalse('password' in resp.content)

        resp = self.c.post(reverse('settings'), {'full_name': 'test',
            'submit': 'general'})
        self.assertTrue('success' in resp.context)
        self.assertEqual(resp.context['success'],
                         'Full name has been successfully changed.')

        self.u.get_profile().email_registered = True
        self.u.get_profile().save()

        resp = self.c.post(reverse('settings'), {'full_name': 'test',
            'email': 'test@test.org', 'submit': 'general'})
        self.assertTrue('success' in resp.context)
        self.assertEqual(resp.context['success'],
                         'Full name has been successfully changed.')

        # Password change
        resp = self.c.post(reverse('settings'), {'old_password': 'test2',
            'submit': 'password'})
        self.assertFormError(resp, 'password_form', 'old_password',
            'Your old password was entered incorrectly. '
            'Please enter it again.')

        resp = self.c.post(reverse('settings'), {'old_password': 'test',
            'submit': 'password', 'new_password1': 'test2',
            'new_password2': 'test2'},
            follow=True)
        self.assertIn('success', resp.context)

        # Alerts
        resp = self.c.post(reverse('settings'), {'alerts': None,
            'submit': 'alerts'})
        self.assertFormError(resp, 'alerts_form', 'alerts', [])

        resp = self.c.post(reverse('settings'), {'alerts': 'alerts',
            'submit': 'alerts'},
            follow=True)
        self.assertIn('success', resp.context)

        resp = self.c.post(reverse('settings'), {'submit': 'wrongsubmit'})
        self.assertTemplateUsed(resp, 'main/settings.html')
        self.assertNotIn('error', resp.context)
        self.assertNotIn('success', resp.context)

    def testAssociation(self):
        resp = self.c.get(reverse('settings'), follow=True)
        self.assertNotIn('facebook', resp.context)
        self.assertNotIn('google', resp.context)
        self.assertNotIn('twitter', resp.context)
        self.assertNotIn('odesk', resp.context)

        self.u.get_profile().odesk_uid = 1
        self.u.get_profile().full_name = "Testing Test"
        self.u.get_profile().save()

        Worker.objects.create_odesk(external_id=1).save()
        # Odesk assoc
        resp = self.c.get(reverse('settings'))
        self.assertIn('odesk', resp.context)

        # Facebook assoc
        usa = UserSocialAuth(user=self.u, provider='facebook', uid='Tester')
        usa.save()

        resp = self.c.get(reverse('settings'))
        self.assertIn('facebook', resp.context)

        # Google assoc
        usa = UserSocialAuth(user=self.u, provider='google-oauth2', uid='Tester')
        usa.save()

        resp = self.c.get(reverse('settings'))
        self.assertIn('google', resp.context)

        # Twitter assoc
        usa = UserSocialAuth(user=self.u, provider='twitter', uid='Tester')
        usa.save()

        resp = self.c.get(reverse('settings'))
        self.assertIn('twitter', resp.context)


class ProjectTests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.c = Client()
        self.c.login(username='testing', password='test')

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

        testUrl = 'http://google.com'
        self.c.post(reverse('project_classifier_view', args=[1]),
            {'test-urls': testUrl}, follow=True)

        # Classification request
        self.assertEqual(ClassifiedSample.objects.all().count(), 1)
        # New sample (new sample shares url with gold sample)
        self.assertEqual(Sample.objects.filter(url=testUrl, job=job).count(),
            1)

        self.c.post(reverse('project_classifier_view', args=[1]),
            {'test-urls': testUrl}, follow=True)

        # classification request + old data
        self.assertEqual(ClassifiedSample.objects.all().count(), 2)
        # old data + new sample
        self.assertEqual(Sample.objects.filter(job=job).count(),
            1)

        # Create a new job and check uniqueness
        job = Job.objects.create_active(
            title='test',
            description='test',
            account=self.u.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        self.c.post(reverse('project_classifier_view', args=[job.id]),
            {'test-urls': testUrl}, follow=True)

        # classification request + old data
        self.assertEqual(ClassifiedSample.objects.all().count(), 3)
        # old data, no new sample since this is the same url
        self.assertEqual(Sample.objects.filter(job=job).count(), 1)

    def testWorkersView(self):
        job = Job.objects.create_active(
            title='test',
            description='test',
            account=self.u.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )
        resp = self.c.get(
            reverse('project_workers_view', args=[job.id]),
            follow=True
        )
        self.assertIn('workers', resp.context)
        self.assertFalse(resp.context['workers'])

        w = Worker.objects.all()
        if w:
            w = w[0]
            resp = self.c.get(
                reverse('project_worker_view', args=[job.id, w.id]),
                follow=True
            )
            self.assertIn('name', resp.context)
            self.assertTrue(resp.context['name'])

    def testDataView(self):
        job = Job.objects.create_active(
            title='test',
            description='test',
            account=self.u.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )
        resp = self.c.get(
            reverse('project_data_view', args=[job.id]),
            follow=True
        )
        self.assertIn('data_set', resp.context)
        self.assertTrue(resp.context['data_set'])

        s = Sample.objects.filter(job=job)
        if s:
            s = s[0]
            resp = self.c.get(
                reverse('project_data_detail', args=[job.id, s.id]),
                follow=True
            )
            self.assertIn('sample', resp.context)
            self.assertTrue(resp.context['sample'])


class DocsTest(TestCase):
    def testDocs(self):
        c = Client()

        c.get(reverse('readme_view'), follow=True)
        self.assertTrue(True)


class ApiTests(TestCase):

    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='testing', password='test')

        self.c = Client()

    def testJobs(self):
        resp = self.c.get('/api/v1/job/?format=json', follow=True)

        # Unauthorized
        self.assertEqual(resp.status_code, 401)

        Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        resp = self.c.get('%s%s?format=json' % (self.api_url, 'job/1/'),
            follow=True)

        # We are not logged in, can't see the job. Unauthorized
        self.assertEqual(resp.status_code, 401)

        self.c.login(username='testing', password='test')

        resp = self.c.get('/api/v1/job/?format=json', follow=True)

        array = json.loads(resp.content)
        self.assertIn('meta', array)
        self.assertEqual(array['meta']['total_count'], 1)

        resp = self.c.get('%s%s?format=json' % (self.api_url, 'job/1/'),
            follow=True)

        self.assertEqual(resp.status_code, 200)
        array = json.loads(resp.content)
        self.assertIn('sample_gathering_url', array)
        self.assertIn('sample_voting_url', array)

        resp = self.c.get('%s%s?format=json' % (self.api_url, 'job/2/'),
            follow=True)

        # Non-existant job.
        self.assertEqual(resp.status_code, 404)

        resp = self.c.get('%s%s?format=json'
            % (self.api_url, 'job/1/feed/'), follow=True)

        array = json.loads(resp.content)
        self.assertIn('entries', array)
        self.assertIn('count', array)
        count = array['count']
        self.assertTrue(count > 0)

        u = User.objects.create_user(username='test2', password='!')
        self.c.login(username='test2', password='!')

        job = Job.objects.create_active(
            account=u.get_profile(),
            data_source=0,
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        resp = self.c.get('%sjob/%d/?format=json' % (self.api_url, job.id),
            follow=True)

        # We are not logged in, can't see the job. Unauthorized
        array = json.loads(resp.content)
        self.assertNotIn('sample_gathering_url', array)
        self.assertNotIn('sample_voting_url', array)

        resp = self.c.get('%s%s?format=json' % (self.api_url, 'job/1/'),
            follow=True)

        # Can't access others' job
        self.assertEqual(resp.status_code, 404)

        u.is_superuser = True
        u.save()

        resp = self.c.get('%s%s?format=json' % (self.api_url, 'job/1/'),
            follow=True)

        # Can access others' jobs if superuser
        self.assertEqual(resp.status_code, 200)

    def testClassifier(self):
        self.c.login(username='testing', password='test')
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        resp = self.c.get('%s%s?format=json' % (self.api_url, 'job/1/classifier/'),
            follow=True)

        array = json.loads(resp.content)
        self.assertIn('absolute_url', array)
        self.assertIn('no_count', array)
        self.assertIn('performance', array)
        self.assertIn('broken_count', array)
        self.assertIn('yes_count', array)

        # Classify an URL
        data = {
            'test-type': 'urls',
            'url': 'google.com',
        }
        resp = self.c.post('%s%s?format=json'
            % (self.api_url, 'job/1/classifier/classify/'), data=data, follow=True)

        array = json.loads(resp.content)
        self.assertIn('request_id', array)
        self.assertIn('status_url', array)

        req_id = array['request_id']
        resp = self.c.get('%s%s?format=json&request_id=%d'
            % (self.api_url, 'job/1/classifier/status/', req_id), follow=True)

        # We are doing it eagerly, should be done already.
        array = json.loads(resp.content)
        self.assertIn('status', array)
        self.assertIn('sample', array)

        data = {
            'test-type': 'urls',
        }
        resp = self.c.post('%s%s?format=json'
            % (self.api_url, 'job/1/classifier/classify/'), data=data, follow=True)

        array = json.loads(resp.content)
        self.assertIn('error', array)
        self.assertEqual(resp.status_code, 404)

        # Classify some URL
        urls = ['google.com', 'google.com', '']
        data = {
            'test-type': 'urls',
            'urls': json.dumps(urls),
        }
        resp = self.c.post('%s%s?format=json'
            % (self.api_url, 'job/1/classifier/classify/'), data=data, follow=True)

        array = json.loads(resp.content)
        self.assertIn('request_id', array)
        self.assertIn('status_url', array)

        idx = 0
        for req in array['request_id']:
            self.assertEqual(req['url'], urls[idx])
            idx += 1

        # Last item shouldn't appear in the response
        self.assertEqual(idx, len(urls) - 1)

        for req_id in array['request_id']:
            resp = self.c.get('%s%s?format=json&request_id=%d'
                % (self.api_url, 'job/1/classifier/status/', req_id['id']), follow=True)

            # We are doing it eagerly, should be done already.
            array = json.loads(resp.content)
            self.assertIn('status', array)
            self.assertIn('sample', array)

        resp = self.c.get('%s%s?format=json&limit=10'
            % (self.api_url, 'job/1/classifier/history/'), follow=True)

        array = json.loads(resp.content)
        self.assertIn('entries', array)
        self.assertIn('count', array)
        count = array['count']
        self.assertTrue(count > 0)

        resp = self.c.get('%s%s?format=json&request_id=%d'
            % (self.api_url, 'job/1/classifier/status/', 5), follow=True)

        # We are doing it eagerly, should be done already.
        array = json.loads(resp.content)
        self.assertIn('error', array)
        self.assertEqual(resp.status_code, 404)

        cs = ClassifiedSample.objects.create(job=job)
        resp = self.c.get('%s%s?format=json&request_id=%d'
            % (self.api_url, 'job/1/classifier/status/', cs.id), follow=True)

        # We are doing it eagerly, should be done already.
        array = json.loads(resp.content)
        self.assertIn('status', array)
        self.assertEqual(len(array), 1)

    def testTools(self):
        num = '0'
        self.assertEqual(sanitize_positive_int(num), 0)

        for num in ['-1', '0x20', None, 'testing', -1]:
            with self.assertRaises(ImmediateHttpResponse):
                sanitize_positive_int(num)

        num = '20'
        self.assertEqual(sanitize_positive_int(num), 20)

        test_list = range(20)
        with self.assertRaises(ImmediateHttpResponse):
            paginate_list(test_list, -1, 0, '')
            paginate_list(test_list, 0, -1, '')

        res = paginate_list(test_list, 10, 0, '')
        self.assertEqual(res['next_page'], '?limit=10&offset=10')
        self.assertEqual(res['entries'], test_list[:10])
        self.assertEqual(res['total_count'], 20)
        self.assertEqual(res['count'], 10)
        self.assertEqual(res['offset'], 0)
        self.assertEqual(res['limit'], 10)

        res = paginate_list(test_list, 20, 10, '')
        self.assertEqual(res['next_page'], '?limit=20&offset=10')
        self.assertEqual(res['entries'], test_list[10:20])
        self.assertEqual(res['total_count'], 20)
        self.assertEqual(res['count'], 10)
        self.assertEqual(res['offset'], 10)
        self.assertEqual(res['limit'], 20)

    def testAlertResource(self):
        self.c.login(username='testing', password='test')
        Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        log = LogEntry.objects.all()[:1][0]
        res = AlertResource().raw_detail(log=log)
        self.assertEqual(res['id'], log.id)
        self.assertEqual(res['type'], log.log_type)
        self.assertEqual(res['job_id'], log.job_id)
        self.assertEqual(res['date'], log.date.strftime('%Y-%m-%d %H:%M:%S'))
        self.assertEqual(res['single_text'], log.get_single_text())
        self.assertEqual(res['plural_text'], log.get_plural_text())
        self.assertEqual(res['box'], log.get_box())

    def testClassifiedSampleResource(self):
        self.c.login(username='testing', password='test')
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        cs = ClassifiedSample.objects.create(job=job)
        res = ClassifiedSampleResource().raw_detail(class_id=cs.id)
        self.assertEqual(res['finished'], cs.is_successful())
        self.assertEqual(res['job_id'], job.id)
        self.assertEqual(res['screenshot'], '')
        self.assertEqual(res['url'], cs.url)
        self.assertEqual(res['sample_url'], '')
        self.assertEqual(res['label_probability'], cs.label_probability)
        self.assertEqual(res['id'], cs.id)
        self.assertEqual(res['label'], cs.label)

        sample = Sample.objects.all()[0]
        cs.sample = sample
        cs.url = sample.url
        cs.save()

        res = ClassifiedSampleResource().raw_detail(class_id=cs.id)
        self.assertEqual(res['finished'], cs.is_successful())
        self.assertEqual(res['screenshot'], sample.screenshot)
        self.assertEqual(res['url'], sample.url)

        sample.screenshot = 'test'
        sample.save()

        res = ClassifiedSampleResource().raw_detail(class_id=cs.id)
        self.assertEqual(res['screenshot'], sample.screenshot)

    def testWorkerResource(self):
        self.c.login(username='testing', password='test')
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        Sample.objects.create_by_worker(
            url='http://google.com',
            job_id=job.id,
            source_val='1',
        )

        w = Worker.objects.get_tagasauris(worker_id='1')
        res = self.c.get('%sjob/%s/worker/%s/?format=json'
            % (self.api_url,job.id, w.id))

        res = json.loads(res.content)
        self.assertEqual(res['earned'], 0)
        self.assertEqual(res['hours_spent'], 0)
        self.assertEqual(res['id'], w.id)
        self.assertEqual(res['urls_collected'], 1)
        self.assertEqual(res['votes_added'], 0)
        self.assertIn('start_time', res)

    def testAdmin(self):
        resp = self.c.get('%sadmin/updates/?format=json' % (self.api_url))

        # Not logged in users can't access admin resource
        self.assertEqual(resp.status_code, 401)

        self.c.login(username='testing', password='test')
        resp = self.c.get('%sadmin/updates/?format=json' % (self.api_url))

        # No-superuser users can't access admin resource
        self.assertEqual(resp.status_code, 401)

        u = User.objects.create_user(username='test2', password='!')
        u.is_superuser = True
        u.save()

        self.c.login(username='test2', password='!')
        resp = self.c.get('%sadmin/updates/?format=json' % (self.api_url))

        self.assertEqual(resp.status_code, 200)
        array = json.loads(resp.content)
        self.assertEqual(array['total_count'], 0)

        Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        resp = self.c.get('%sadmin/updates/?format=json' % (self.api_url))

        self.assertEqual(resp.status_code, 200)
        array = json.loads(resp.content)
        self.assertTrue(array['total_count'] > 0)
        self.assertEqual(len(array['entries']), array['count'])


class TestAdmin(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='test2', password='1')

    def testIndex(self):
        c = Client()
        c.login(username='test2', password='1')

        r = c.get(reverse('admin_index'), follow=True)
        self.assertEqual(r.status_code, 404)

        self.u.is_superuser = True
        self.u.save()

        r = c.get(reverse('admin_index'), follow=True)
        self.assertEqual(r.status_code, 200)

        u = User.objects.create_user(username='test3', password='1')
        j = Job.objects.create_active(
            account=u.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}])
        )

        r = c.get(reverse('admin_index'), follow=True)
        self.assertIn(j, r.context['projects'])

        r = c.get(reverse('project_view', args=[j.id]), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertFalse('error' in r.context)
