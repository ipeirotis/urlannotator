import urllib2
import threading
import subprocess
from Queue import Queue

from django.test import TestCase

from urlannotator.tools.web_extractors import (get_web_screenshot, get_web_text,
    is_proper_url)
from urlannotator.tools.synchronization import RWSynchronize247, POSIXLock
from urlannotator.tools.webkit2png import BaseWebkitException


class WebExtractorsTests(TestCase):

    def testWebTextExtractor(self):
        text = get_web_text('http://google.com')
        self.assertTrue('google' in text)

        # Bad url should raise an exception
        with self.assertRaises(subprocess.CalledProcessError):
            get_web_text('weeeeeeeeeeeeeeeeeeeeeee')
        # text = get_web_text('10clouds.com')
        # self.assertTrue('10Clouds' in text)
        # self.assertTrue('We make great apps' in text)

    def testWebScreenshotExtractor(self):
        screenshot = get_web_screenshot('http://google.com')

        s = urllib2.urlopen(screenshot)
        self.assertEqual(s.headers.type, 'image/jpeg')

        # Bad url should raise an exception
        with self.assertRaises(BaseWebkitException):
            get_web_screenshot('weeeeeeeeeeeeeeeeeeeeeee')


class SynchronizationTests(TestCase):

    def testSynchronization247(self):

        class TestClass(object):
            read_counter = 0
            max_read_counter = 0

            write_counter = 0
            max_write_counter = 0

            def __init__(self, q, lock, unique):
                self.q = q
                self.lock = lock
                self.unique = unique
                self.sync247 = RWSynchronize247('testSynchronization247%s' % unique)

            def readSth(self, queues):

                self.sync247.reader_lock()
                self.lock.acquire()
                self.read_counter += 1
                self.__class__.max_read_counter = max(
                    self.read_counter,
                    self.__class__.max_read_counter)
                self.lock.release()

                self.lock.acquire()
                self.__class__.read_counter -= 1
                self.lock.release()
                self.sync247.reader_release()

            def writeSth(self, queues):

                self.sync247.modified_lock()
                self.lock.acquire()
                self.write_counter += 1
                self.__class__.max_write_counter = max(
                    self.write_counter,
                    self.__class__.max_write_counter)
                self.lock.release()

                self.lock.acquire()
                self.write_counter -= 1
                self.lock.release()
                self.sync247.modified_release()

        def read_thread(queues, lock):
            tc = TestClass(queues, lock, 'a')
            queues['r'].get(block=True)
            queues['s'].put('b')
            tc.readSth(queues)

        def write_thread(queues, lock):
            tc = TestClass(queues, lock, 'a')
            queues['w'].get(block=True)
            queues['s'].put('b')
            tc.writeSth(queues)

        # from tenclouds.stacktracer import trace_start, trace_stop
        # trace_start("trace.html", interval=5, auto=True)

        def test_schema(test, schema=['w', 'w', 'w', 'r'],
                writers=3, readers=1):
            """
                Allows semi-synchronizingly test RWLock. We can't go any deeper
                with atomicity due to technical reasons of semaphore testing.

                Makes every writer and reader be able to enter critical section
                in the specified order. Yet, no assumptions should be done as
                when a thread really enters the critical section.
            """

            TestClass.read_counter = 0
            TestClass.write_counter = 0
            TestClass.max_write_counter = 0
            TestClass.max_read_counter = 0

            queues = {
                'w': Queue(),
                'r': Queue(),
                's': Queue(),
            }

            lock = threading.Lock()
            rthreads = []
            for _ in range(readers):
                rthreads.append(
                    threading.Thread(target=read_thread, args=(queues, lock))
                )

            wthreads = []
            for _ in range(writers):
                wthreads.append(threading.Thread(target=write_thread,
                    args=(queues, lock)))

            for th in wthreads + rthreads:
                th.start()

            for op in schema:
                queues[op].put('x')
                queues['s'].get(block=True)

            for th in wthreads + rthreads:
                th.join()

            test.assertTrue(TestClass.max_read_counter >= 1 or not readers)
            test.assertTrue(TestClass.max_write_counter == 1 or not writers)

        test_schema(self)
        test_schema(self, schema=['w', 'r'], writers=1, readers=1)
        test_schema(self, schema=['r', 'r'], writers=0, readers=2)
        test_schema(self, schema=['w', 'w'], writers=2, readers=0)
        test_schema(self, schema=['w', 'r', 'r', 'w', 'r', 'w', 'r', 'w', 'w',
            'r', 'r', 'r', 'w', 'w', 'r', 'w', 'w', 'w', 'r', 'r'],
            writers=10, readers=10)
        # trace_stop()


class POSIXCacheTest(TestCase):
    def testPOSIXCache(self):
        lock = POSIXLock(name='cache-test')
        lock_two = POSIXLock(name='cache-test')
        self.assertEqual(lock.lock, lock_two.lock)

        lock_id = id(lock.lock)

        # Drop locks' ref count to 0 - instant garbage collection
        del lock, lock_two

        # Create a different lock so that an attempt to create a lock with
        # previous name results in an object of different id.
        #
        # This one was important here, so that a reference is kept and the
        # following lock call is spawned with different id, yet with the same
        # inner lock id (caching) until the equality is tested.
        lock_two = POSIXLock(name='cache-test2')
        lock = POSIXLock(name='cache-test')

        # Make sure we will unlink no longer used resources.
        self.assertFalse(id(lock.lock) == lock_id)


class URLCheckTest(TestCase):
    def testURLCheck(self):
        tests = [
            ('127.0.0.1', False),
            (':10', False),
            (':', False),
            ('10.0.0.1:2414', False),
            ('172.16.0.1:21021', False),
            ('192.168.0.100', False),
            ('213.241.87.50', True),
            ('213.241.87.50:80', True),
            ('213.241.87.50:232232', True),
        ]

        for test in tests:
            self.assertEqual(is_proper_url(test[0]), test[1])
