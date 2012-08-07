import urllib2
import time
import threading
from Queue import Queue

from django.test import TestCase

from urlannotator.tools.web_extractors import get_web_screenshot, get_web_text
from urlannotator.tools.synchronization import RWSynchronize247


class WebExtractorsTests(TestCase):

    def testWebTextExtractor(self):
        text = get_web_text('google.com')
        self.assertTrue('google' in text)

        # text = get_web_text('10clouds.com')
        # self.assertTrue('10Clouds' in text)
        # self.assertTrue('We make great apps' in text)

    def testWebScreenshotExtractor(self):
        screenshot = get_web_screenshot('google.com')

        s = urllib2.urlopen(screenshot)
        self.assertEqual(s.headers.type, 'image/png')


class SynchronizationTests(TestCase):

    def testSynchronization247(self):

        class TestClass(object):
            read_counter = 0
            max_read_counter = 0

            write_counter = 0
            max_write_counter = 0

            def __init__(self, q, lock, unique, test):
                self.q = q
                self.lock = lock
                self.unique = unique
                self.test = test

            def readSth(self):
                self.lock.acquire()
                self.read_counter += 1
                self.__class__.max_read_counter = max(
                    self.read_counter,
                    self.__class__.max_read_counter)
                self.lock.release()

                self.test.assertTrue(self.write_counter == 0)
                time.sleep(1)

                self.lock.acquire()
                self.__class__.read_counter -= 1
                self.lock.release()

            def writeSth(self):

                self.lock.acquire()
                self.write_counter += 1
                self.__class__.max_write_counter = max(
                    self.write_counter,
                    self.__class__.max_write_counter)
                self.lock.release()

                self.test.assertTrue(self.read_counter == 0)
                print self.write_counter
                self.test.assertTrue(self.write_counter == 1)
                time.sleep(1)
                # self.q.put(self.unique)

                self.lock.acquire()
                self.write_counter -= 1
                self.lock.release()


        def read_thread(q, inst1, inst2):
            rw = RWSynchronize247('testSynchronization247', inst1, inst2,
                reader_functions=['readSth'], writer_functions=['writeSth'])
            for _ in range(0, 1):
                rw.readSth()

        def write_thread(q, inst1, inst2):
            rw = RWSynchronize247('testSynchronization247', inst1, inst2,
                reader_functions=['readSth'], writer_functions=['writeSth'])
            for _ in range(0, 1):
                rw.writeSth()

        q = Queue()
        lock = threading.Lock()
        inst1 = TestClass(q, lock, 'a', self)
        inst2 = TestClass(q, lock, 'b', self)
        thread1 = threading.Thread(target=read_thread, args=(q, inst1, inst2))
        thread2 = threading.Thread(target=read_thread, args=(q, inst1, inst2))

        wthreads = []
        for _ in range(0, 2):
            wthreads.append(threading.Thread(target=write_thread,
                args=(q, inst1, inst2)))

        # thread1.start()
        # thread2.start()
        for th in wthreads:
            th.start()

        # thread1.join()
        # thread2.join()
        for th in wthreads:
            th.join()

        self.assertTrue(TestClass.max_read_counter > 1)
        self.assertTrue(TestClass.max_write_counter == 1)
