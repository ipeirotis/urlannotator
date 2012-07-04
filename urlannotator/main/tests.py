from django.test import TestCase
from django.test.client import Client
from urlannotator.main.views import get_activation_key
from urlannotator.main.models import UserProfile
from django.contrib.auth.models import User

class BaseNotLoggedInTests(TestCase):
  def testLoginNotRestrictedPages(self):
    url_list = [('', 'main/index.html'), ('/login', 'main/login.html'),
                ('/register', 'main/register.html'),]
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
    url_list = [('/setttings', 'main/settings.html'), ('/wizard', 'main/wizard/project.html')]
    for url, template in url_list:
      c = Client()

      self.assertRaises(c.get(url))

  def testEmailRegister(self):
    c = Client()
    resp = c.post('/register', {'email': 'testtest.test', 'password1': 'test1', 'password2': 'test'})
    self.assertFormError(resp, 'form', None, 'Passwords do not match.')
    self.assertFormError(resp, 'form', 'email', 'Enter a valid e-mail address.')
    
    resp = c.post('/register', {'email': 'test@test.test', 'password1': 'test', 'password2': 'test'})
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
    
    resp = c.post('/register', {'email': 'test@test.test', 'password1': 'test1', 'password2': 'test'})
    self.assertFormError(resp, 'form', None, 'Passwords do not match.')
    self.assertFormError(resp, 'form', 'email', 'Email is already in use.')
    
    resp = c.post('/login', {'email': 'test@test.test', 'password': 'test'})
    self.assertEqual(resp.status_code, 302) # redirection
