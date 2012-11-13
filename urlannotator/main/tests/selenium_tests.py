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


class ProjectWizardSeleniumTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(ProjectWizardSeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(ProjectWizardSeleniumTests, cls).tearDownClass()

    def assertHiddenElements(self, el):
        for element in el:
            e = self.selenium.find_element_by_id(element)
            e = e.find_element_by_xpath('../..')
            self.assertTrue(e)
            self.assertEqual(e.value_of_css_property('display'), 'none')

    def assertShownElements(self, el):
        for element in el:
            e = self.selenium.find_element_by_id(element)
            e = e.find_element_by_xpath('../..')
            self.assertTrue(e)
            self.assertNotEqual(e.value_of_css_property('display'), 'none')

    def test_formLayout(self):
        login(self.selenium, self.live_server_url + "/login/")
        self.selenium.get('%s%s'
                          % (self.live_server_url, reverse('project_wizard')))

        self.assertTrue(self.selenium.find_element_by_id('id_topic'))
        self.assertTrue(self.selenium.find_element_by_id('id_topic_desc'))
        self.assertTrue(self.selenium.find_element_by_id('id_data_source'))

        selector_free = 'select#id_data_source option[value="0"]'
        selector_paid = 'select#id_data_source option[value="2"]'

        # NoSuchElementException - missing odesk options
        with self.assertRaises(exceptions.NoSuchElementException):
            self.selenium.find_element_by_css_selector(selector_free)
            self.selenium.find_element_by_css_selector(selector_paid)

        shown_elements = ['id_no_of_urls']
        self.assertShownElements(shown_elements)

        hidden_elements = ['id_project_type',
                           'id_hourly_rate',
                           'id_budget']
        self.assertHiddenElements(hidden_elements)

        user = User.objects.all()[0]
        prof = user.get_profile()
        prof.odesk_uid = 'test'
        prof.save()

        self.selenium.get('%s%s'
                          % (self.live_server_url, reverse('project_wizard')))
        # User connected to odesk - diplay odesk options
        self.selenium.find_element_by_css_selector(selector_free)
        self.selenium.find_element_by_css_selector(selector_paid)

        # Data source changing - change displayed project types etc.
        data_source = self.selenium.find_element_by_id('id_data_source')
        project_type = self.selenium.find_element_by_id('id_project_type')
        # Odesk free, fixed number of urls automatically selected
        opt = data_source.find_element_by_xpath('.//option[@value="0"]')
        opt.click()

        shown_elements = ['id_project_type', 'id_no_of_urls', 'id_hourly_rate']
        self.assertShownElements(shown_elements)

        hidden_elements = ['id_budget']
        self.assertHiddenElements(hidden_elements)

        # Fixed price
        selector = './/option[@value="1"]'
        project_opt = project_type.find_element_by_xpath(selector)
        project_opt.click()

        shown_elements = ['id_project_type', 'id_budget']
        self.assertShownElements(shown_elements)

        hidden_elements = ['id_no_of_urls', 'id_hourly_rate']
        self.assertHiddenElements(hidden_elements)

        # Own workforce
        opt = data_source.find_element_by_xpath(selector)
        opt.click()

        shown_elements = ['id_no_of_urls']
        self.assertShownElements(shown_elements)

        hidden_elements = ['id_project_type',
                           'id_hourly_rate',
                           'id_budget']
        self.assertHiddenElements(hidden_elements)

        # Odesk paid
        opt = data_source.find_element_by_xpath('.//option[@value="2"]')
        opt.click()

        shown_elements = ['id_project_type',
                          'id_no_of_urls',
                          'id_hourly_rate']
        self.assertShownElements(shown_elements)

        hidden_elements = ['id_budget']
        self.assertHiddenElements(hidden_elements)

        project_opt.click()

        shown_elements = ['id_project_type', 'id_budget']
        self.assertShownElements(shown_elements)

        hidden_elements = ['id_no_of_urls', 'id_hourly_rate']
        self.assertHiddenElements(hidden_elements)


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
