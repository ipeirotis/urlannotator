from django.test import LiveServerTestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.common import exceptions


def login(driver, url):
    u = User.objects.create_user(username='test@10clouds.com',
            email='test@10clouds.com', password='test')
    p = u.get_profile()
    p.email_registered = True
    p.activation_key = 'actived'
    p.save()
    u.is_active = True
    u.save()
    driver.get(url)
    driver.find_element_by_id("id_email").clear()
    driver.find_element_by_id("id_email").send_keys("test@10clouds.com")
    driver.find_element_by_id("id_password").clear()
    driver.find_element_by_id("id_password").send_keys("test")
    driver.find_element_by_css_selector("button.btn.btn-primary").click()


class RegistrationSeleniumTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(RegistrationSeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(RegistrationSeleniumTests, cls).tearDownClass()

    def test_registerServices(self):
        services = [('google-oauth2', 'google.com'),
                    ('twitter', 'twitter.com'),
                    ('facebook', 'facebook.com')]
        for name, url_part in services:
            self.selenium.get('%s%s'
                              % (self.live_server_url,
                                 reverse('register_service', args=[name])))
            self.assertIn(url_part, self.selenium.current_url)

        self.selenium.get('%s%s'
                          % (self.live_server_url, reverse('odesk_register')))
        self.assertIn('odesk.com', self.selenium.current_url)

    def test_logInAndOut(self):
        login(self.selenium, self.live_server_url + "/login/")
        alert = self.selenium.find_element_by_class_name('alert-success')
        self.assertTrue(alert)

        self.selenium.get('%s%s'
                          % (self.live_server_url, reverse('logout')))
        el = self.selenium.find_element_by_class_name("btn-login")
        self.assertTrue(el)


class DashboardSeleniumTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(DashboardSeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(DashboardSeleniumTests, cls).tearDownClass()

    def test_projectList(self):
        self.selenium.get('%s%s' % (self.live_server_url, reverse('index')))
        with self.assertRaises(exceptions.NoSuchElementException):
            self.selenium.find_element_by_id('nothing-to-display')

        login(self.selenium, self.live_server_url + "/login/")
        self.selenium.find_element_by_id('nothing-to-display')


class SettingsSeleniumTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(SettingsSeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(SettingsSeleniumTests, cls).tearDownClass()

    def test_formLayout(self):
        login(self.selenium, self.live_server_url + "/login/")
        self.selenium.get('%s%s' % (self.live_server_url, reverse('settings')))
        self.assertTrue(self.selenium.find_element_by_id('id_full_name'))
        self.assertTrue(self.selenium.find_element_by_id('id_email'))
        self.assertTrue(self.selenium.find_element_by_id('id_old_password'))
