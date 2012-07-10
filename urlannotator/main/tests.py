from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from urlannotator.main.views import get_activation_key
from urlannotator.main.models import UserProfile, UserOdeskAssociation,\
    Project

class BaseNotLoggedInTests(TestCase):
    def testLoginNotRestrictedPages(self):
        url_list = [('', 'main/index.html'), (reverse('login'), 'main/login.html'),
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
        url_list = [('/setttings/', 'main/settings.html'), ('/wizard/', 'main/wizard/project.html')]
        for url, template in url_list:
            c = Client()

            self.assertRaises(c.get(url))

    def testEmailRegister(self):
        c = Client()

        register_url = reverse('register')
        resp = c.post(register_url, {'email': 'testtest.test', 'password1': 'test1', 'password2': 'test'})
        self.assertFormError(resp, 'form', None, 'Passwords do not match.')
        self.assertFormError(resp, 'form', 'email', 'Enter a valid e-mail address.')
        
        resp = c.post(register_url, {'email': 'test@test.test', 'password1': 'test', 'password2': 'test'})
        user = User.objects.get(email='test@test.test')
        key = get_activation_key(user.email, user.id)
        self.assertFalse(user.is_active)
        self.assertEqual(user.get_profile().activation_key, key)
        self.assertTrue(user.get_profile().email_registered)
        
        bad_key = 'thisisabadkey'
        resp = c.get('/activation/%s' % bad_key)
        self.assertTrue('error' in resp.context)
        
        resp = c.get('/activation/%s' % key)
        self.assertTrue('success' in resp.context)
        self.assertEqual(UserProfile.objects.get(id=1).activation_key, 'activated')

        resp = c.get('/activation/%s' % key)
        self.assertTrue('error' in resp.context)
        
        resp = c.post(register_url, {'email': 'test@test.test', 'password1': 'test1', 'password2': 'test'})
        self.assertFormError(resp, 'form', None, 'Passwords do not match.')
        self.assertFormError(resp, 'form', 'email', 'Email is already in use.')
        
        resp = c.post(reverse('login'), {'email': 'test@test.test', 'password': 'test'})
        # Redirection
        self.assertEqual(resp.status_code, 302)

class LoggedInTests(TestCase):
    def createProject(self, user):
        p = Project(author=user,
                    topic='test',
                    topic_desc='test desc',
                    data_source=1,
                    project_status=1)  # Active
        p.save()

    def testDashboard(self):
        c = Client()
        u = User.objects.create_user(username='test', password='test', email='test@test.org')
        c.login(username='test', password='test')

        resp = c.get(reverse('index'))

        # Empty projects list
        self.assertTrue('projects' in resp.context)
        self.assertTrue(not resp.context['projects'])

        # Populate projects
        self.createProject(u)
        self.createProject(u)

        self.assertTrue(Project.objects.all().count() == 2)
        resp = c.get(reverse('index'))

        self.assertTrue('projects' in resp.context)
        self.assertTrue(len(resp.context['projects']) == 2)
        self.assertFalse('Nothing to display' in resp.content)

class SettingsTests(TestCase):
    def testBasic(self):
        c = Client()
        u = User.objects.create_user(username='test', password='test', email='test@test.org')
        c.login(username='test', password='test')

        # No odesk association - display alert
        resp = c.get(reverse('project_wizard'))

        self.assertTrue(resp.status_code in [200, 302])
        self.assertTrue('wizard_alert' in resp.context)

        # Invalid option - odesk chosen, account not connected
        odesk_sources = ['0', '2']
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
            self.assertFormError(resp, 'attributes_form', None, 'You have to be connected to Odesk to use this option.')
        uoa = UserOdeskAssociation(user=u)
        uoa.save()

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
        self.assertFormError(resp, 'topic_form', 'topic', 'Please input project topic.')

        data = {'topic': 'Test',
                'data_source': '1',
                'project_type': '0',
                'no_of_urls': '0',
                'hourly_rate': '1.0',
                'budget': '1.0',
                'same_domain': '0',
                'submit': 'draft'}

        resp = c.post(reverse('project_wizard'), data)
        self.assertFormError(resp, 'topic_form', 'topic_desc', 'Please input project topic description.')
