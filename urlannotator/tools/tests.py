import urllib2

from django.test import TestCase

from urlannotator.tools.web_extractors import get_web_screenshot, get_web_text


class BaseNotLoggedInTests(TestCase):

    def testWebTextExtractor(self):
        text = get_web_text('google.com')
        self.assertTrue('Google' in text)

        # text = get_web_text('10clouds.com')
        # self.assertTrue('10Clouds' in text)
        # self.assertTrue('We make great apps' in text)

    def testWebScreenshotExtractor(self):
        screenshot = get_web_screenshot('google.com')

        s = urllib2.urlopen(screenshot)
        self.assertEqual(s.headers.type, 'image/png')
